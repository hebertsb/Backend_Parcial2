# notifications/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from django.db.models import Count
from django.utils import timezone
from typing import Any, Dict, cast

from .models import DeviceToken, Notification, NotificationPreference
from .serializers import (
    DeviceTokenSerializer,
    DeviceTokenCreateSerializer,
    NotificationSerializer,
    NotificationListSerializer,
    SendNotificationSerializer,
    NotificationPreferenceSerializer,
    NotificationStatsSerializer,
)
from .notification_service import NotificationService
from api.permissions import IsAdminUser


class DeviceTokenViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar tokens de dispositivos.

    Los usuarios solo pueden ver y gestionar sus propios tokens.
    """

    serializer_class = DeviceTokenSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filtrar tokens por usuario actual"""
        return DeviceToken.objects.filter(user=self.request.user)

    @action(detail=False, methods=["post"])
    def register(self, request):
        """Registra un nuevo token de dispositivo para el usuario actual."""
        serializer = DeviceTokenCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = cast(Dict[str, Any], serializer.validated_data)

        device_token = NotificationService.register_device_token(
            user=request.user,
            token=validated_data["token"],
            platform=validated_data.get("platform", DeviceToken.Platform.WEB),
            device_name=validated_data.get("device_name"),
        )

        return Response(DeviceTokenSerializer(device_token).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def unregister(self, request):
        """Desregistra (desactiva) un token de dispositivo."""

        token = request.data.get("token")
        if not token:
            return Response({"error": "Token es requerido"}, status=status.HTTP_400_BAD_REQUEST)

        success = NotificationService.unregister_device_token(token)

        if success:
            return Response({"message": "Token desactivado correctamente"}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Token no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=["get"])
    def my_devices(self, request):
        """Lista todos los dispositivos activos del usuario actual."""

        devices = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(devices, many=True)
        return Response(serializer.data)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para ver notificaciones y endpoints admin de envío."""

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list":
            return NotificationListSerializer
        if self.action == "send":
            return SendNotificationSerializer
        return NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=False, methods=["get"])
    def unread(self, request):
        notifications = self.get_queryset().filter(
            status__in=[Notification.Status.PENDING, Notification.Status.SENT]
        )
        serializer = NotificationListSerializer(notifications, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        count = NotificationService.get_unread_count(request.user)
        return Response({"count": count})

    @action(detail=True, methods=["post"])
    def mark_as_read(self, request, pk=None):
        """Marca una notificación como leída."""

        try:
            notification_id = int(pk)
        except (TypeError, ValueError):
            return Response({"error": "ID de notificación inválido"}, status=status.HTTP_400_BAD_REQUEST)

        success = NotificationService.mark_notification_as_read(notification_id, request.user)

        if success:
            return Response({"message": "Notificación marcada como leída"}, status=status.HTTP_200_OK)
        return Response({"error": "Notificación no encontrada"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=["post"])
    def mark_all_as_read(self, request):
        count = NotificationService.mark_all_as_read(request.user)
        return Response({"message": f"{count} notificaciones marcadas como leídas", "count": count})

    @action(detail=False, methods=["post"], permission_classes=[IsAdminUser])
    def send(self, request):
        """Envía notificaciones: admite user_ids, topic o device_tokens."""

        serializer = SendNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = cast(Dict[str, Any], serializer.validated_data)

        # prioridad: topic > device_tokens > user_ids > admins
        topic = validated_data.get("topic")
        device_tokens = validated_data.get("device_tokens")
        user_ids = validated_data.get("user_ids")

        # asegurarnos de que title y body estén presentes (serializer ya los valida)
        title = validated_data.get("title")
        body = validated_data.get("body")
        if title is None or body is None:
            return Response({"error": "title y body son requeridos"}, status=status.HTTP_400_BAD_REQUEST)

        if topic:
            result = NotificationService.send_notification_to_topic(
                topic=topic,
                title=title,
                body=body,
                notification_type=validated_data.get("notification_type", "SYSTEM"),
                data=validated_data.get("data"),
            )
        elif device_tokens:
            result = NotificationService.send_to_device_tokens(
                tokens=device_tokens,
                title=title,
                body=body,
                notification_type=validated_data.get("notification_type", "CUSTOM"),
                data=validated_data.get("data"),
                image_url=validated_data.get("image_url"),
            )
        elif user_ids:
            users = User.objects.filter(id__in=user_ids, is_active=True)
            result = NotificationService.send_notification_to_users(
                users=list(users),
                title=title,
                body=body,
                notification_type=validated_data.get("notification_type", "CUSTOM"),
                data=validated_data.get("data"),
                image_url=validated_data.get("image_url"),
            )
        else:
            result = NotificationService.send_to_all_admins(
                title=title,
                body=body,
                notification_type=validated_data.get("notification_type", "SYSTEM"),
                data=validated_data.get("data"),
            )

        return Response(result, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        queryset = self.get_queryset()

        stats = {
            "total_notifications": queryset.count(),
            "unread_count": queryset.filter(status__in=[Notification.Status.PENDING, Notification.Status.SENT]).count(),
            "sent_count": queryset.filter(status=Notification.Status.SENT).count(),
            "failed_count": queryset.filter(status=Notification.Status.FAILED).count(),
            "by_type": dict(queryset.values("notification_type").annotate(count=Count("id")).values_list("notification_type", "count")),
            "recent_notifications": queryset[:10],
        }

        serializer = NotificationStatsSerializer(stats)
        return Response(serializer.data)


class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar preferencias de notificaciones."""

    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return NotificationPreference.objects.filter(user=self.request.user)

    @action(detail=False, methods=["get"])
    def my_preferences(self, request):
        preferences, created = NotificationPreference.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(preferences)
        return Response(serializer.data)

    @action(detail=False, methods=["patch"])
    def update_preferences(self, request):
        preferences, created = NotificationPreference.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(preferences, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
