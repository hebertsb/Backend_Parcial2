from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock

from products.models import Product
from sales.models import Order


class StripeCheckoutFlowTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        # Crear usuario proporcionado por el usuario (solo para pruebas locales)
        self.user = User.objects.create_user(username='john@gmil.com', email='john@gmil.com', password='123456')
        # Crear algunos productos
        self.p1 = Product.objects.create(name='Producto A', price=100.00, stock=10)
        self.p2 = Product.objects.create(name='Producto B', price=50.00, stock=5)

    def authenticate(self):
        # Forzar autenticación del cliente de test
        self.client.force_authenticate(user=self.user)

    @patch('sales.views.stripe.checkout.Session.create')
    @patch('sales.views.stripe.Webhook.construct_event')
    def test_full_checkout_and_webhook_flow(self, mock_construct_event, mock_session_create):
        """Simula crear una sesión de checkout y el webhook checkout.session.completed."""
        self.authenticate()

        # 1) Añadir productos al carrito
        res1 = self.client.post('/api/sales/cart/', {'product_id': self.p1.id, 'quantity': 2}, format='json')
        self.assertEqual(res1.status_code, 200)
        res2 = self.client.post('/api/sales/cart/', {'product_id': self.p2.id, 'quantity': 1}, format='json')
        self.assertEqual(res2.status_code, 200)

        # 2) Mockear la creación de la sesión de Stripe
        fake_checkout = MagicMock()
        fake_checkout.url = 'https://checkout.stripe.test/session/xyz'
        fake_checkout.id = 'cs_test_123'
        mock_session_create.return_value = fake_checkout

        # Llamar al endpoint de checkout
        resp = self.client.post('/api/sales/checkout/', {}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('checkout_url', resp.data)

        # Verificar que la orden fue marcada PROCESSING
        order = Order.objects.filter(customer=self.user).order_by('-created_at').first()
        self.assertIsNotNone(order)
        self.assertEqual(order.status, 'PROCESSING')

        # 3) Mockear el webhook de Stripe: construir evento con metadata.order_id
        event = {
            'type': 'checkout.session.completed',
            'data': {
                'object': {
                    'metadata': {'order_id': str(order.id)}
                }
            }
        }
        mock_construct_event.return_value = event

        # Enviar POST al webhook (firma puede ser cualquier string porque lo mockeamos)
        webhook_resp = self.client.post('/api/sales/stripe-webhook/', data=b'{}', HTTP_STRIPE_SIGNATURE='tst')
        self.assertEqual(webhook_resp.status_code, 200)

        # Refrescar la orden
        order.refresh_from_db()
        self.assertEqual(order.status, 'COMPLETED')

        # Verificar que el stock se redujo: p1 quantity 2, p2 quantity 1
        p1 = Product.objects.get(id=self.p1.id)
        p2 = Product.objects.get(id=self.p2.id)
        self.assertEqual(p1.stock, 8)
        self.assertEqual(p2.stock, 4)
