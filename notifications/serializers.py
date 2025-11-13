# notifications/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import DeviceToken, Notification, NotificationPreference


class DeviceTokenSerializer(serializers.ModelSerializer):
    """Serializer para tokens de dispositivos"""
    
    class Meta:
        model = DeviceToken
        fields = ['id', 'token', 'platform', 'device_name', 'is_active', 
                  'created_at', 'updated_at', 'last_used']
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_used', 'is_active']

    def create(self, validated_data):
        # El usuario se obtiene del contexto (request.user)
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class DeviceTokenCreateSerializer(serializers.Serializer):
    """Serializer simplificado para registrar un nuevo token"""
    token = serializers.CharField(max_length=255, required=True)
    platform = serializers.ChoiceField(
        choices=DeviceToken.Platform.choices,
        default=DeviceToken.Platform.WEB
    )
    device_name = serializers.CharField(max_length=100, required=False, allow_blank=True)


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer para notificaciones"""
    username = serializers.CharField(source='user.username', read_only=True)
    is_read = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = ['id', 'user', 'username', 'notification_type', 'title', 'body', 
                  'data', 'status', 'is_read', 'sent_at', 'read_at', 'created_at']
        read_only_fields = ['id', 'user', 'status', 'sent_at', 'read_at', 'created_at']

    def get_is_read(self, obj):
        return obj.status == Notification.Status.READ


class NotificationListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listar notificaciones"""
    is_read = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = ['id', 'notification_type', 'title', 'body', 'is_read', 
                  'created_at', 'sent_at']
        read_only_fields = fields

    def get_is_read(self, obj):
        return obj.status == Notification.Status.READ


class SendNotificationSerializer(serializers.Serializer):
    """Serializer para enviar notificaciones manualmente"""
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="Lista de IDs de usuarios. Si está vacío, se envía a todos los admins"
    )
    topic = serializers.CharField(
        required=False,
        allow_blank=False,
        help_text="Nombre del topic FCM al que enviar (broadcast)"
    )
    device_tokens = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Lista de tokens FCM para envío directo"
    )
    title = serializers.CharField(max_length=200, required=True)
    body = serializers.CharField(required=True)
    notification_type = serializers.ChoiceField(
        choices=Notification.NotificationType.choices,
        default=Notification.NotificationType.CUSTOM
    )
    # 'data' is a convenient input name but the base Serializer defines a
    # property named `data`. Pylance complains about assigning a
    # JSONField to that name (type mismatch). We keep the runtime name
    # for backward compatibility but silence the type checker here.
    data = serializers.JSONField(required=False, allow_null=True)  # type: ignore[assignment]
    image_url = serializers.URLField(required=False, allow_blank=True, allow_null=True)

    def validate_user_ids(self, value):
        if value:
            # Verificar que los usuarios existen
            existing_users = User.objects.filter(id__in=value).count()
            if existing_users != len(value):
                raise serializers.ValidationError(
                    "Algunos IDs de usuarios no existen"
                )
        return value

    def validate(self, attrs):
        """
        Validación general: se permite cualquiera de los siguientes:
        - user_ids (lista de usuarios) OR
        - topic (string) OR
        - device_tokens (lista de tokens) OR
        - ninguno (en cuyo caso se enviará a todos los admins)
        """
        user_ids = attrs.get('user_ids')
        topic = attrs.get('topic')
        device_tokens = attrs.get('device_tokens')

        # Si se pasan device_tokens, asegurar que no esté vacío
        if device_tokens is not None and len(device_tokens) == 0:
            raise serializers.ValidationError({'device_tokens': 'La lista de device tokens no puede estar vacía'})

        # Si se pasan topic, asegurar que no esté vacío
        if topic is not None and str(topic).strip() == '':
            raise serializers.ValidationError({'topic': 'El topic no puede estar vacío'})

        # Nota: no prohibimos combinar campos; la vista elegirá la prioridad.
        return attrs


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer para preferencias de notificaciones"""
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = NotificationPreference
        fields = ['id', 'user', 'username', 'enabled', 'sale_notifications', 
                  'product_notifications', 'report_notifications', 'ml_notifications',
                  'system_notifications', 'quiet_hours_start', 'quiet_hours_end',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class NotificationStatsSerializer(serializers.Serializer):
    """Serializer para estadísticas de notificaciones"""
    total_notifications = serializers.IntegerField()
    unread_count = serializers.IntegerField()
    sent_count = serializers.IntegerField()
    failed_count = serializers.IntegerField()
    by_type = serializers.DictField()
    recent_notifications = NotificationListSerializer(many=True)
