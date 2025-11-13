"""
Generador de datos sintéticos para demostración del sistema de predicción de ventas.
Crea ventas realistas con patrones estacionales, tendencias y variabilidad.
"""
import os
import random
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction, DatabaseError
from django.utils import timezone
from products.models import Product, Category, Brand, Warranty
from sales.models import Order, OrderItem, PaymentMethod

User = get_user_model()


class SalesDataGenerator:
    """
    Genera datos sintéticos de ventas con patrones realistas.
    """
    
    def __init__(self):
        # Generar al menos 24 meses de datos para pruebas de series temporales y predicciones
        self.start_date = timezone.now() - timedelta(days=730)  # ~24 meses atrás
        self.end_date = timezone.now()
        
    def _create_demo_products_if_needed(self) -> List[Product]:
        """Crea productos de demo si no existen."""
        # Verificar si ya hay productos
        existing_products = list(Product.objects.all()[:30])
        if Product.objects.count() >= 30:
            # Asegurar que incluso los productos existentes tengan las métricas pobladas
            for p in existing_products:
                self._ensure_product_metrics(p)
            return existing_products
        
        # Categorías específicas para tienda de electrodomésticos
        categories_data = [
            {'name': 'Heladeras', 'slug': 'heladeras'},
            {'name': 'Lavarropas', 'slug': 'lavarropas'},
            {'name': 'Microondas', 'slug': 'microondas'},
            {'name': 'Televisores', 'slug': 'televisores'},
            {'name': 'Cocinas', 'slug': 'cocinas'},
            {'name': 'Aire Acondicionado', 'slug': 'aire-acondicionado'},
            {'name': 'Pequeños Electrodomésticos', 'slug': 'pequenos-electrodomesticos'},
        ]
        
        categories = []
        for cat_data in categories_data:
            category, _ = Category.objects.get_or_create(
                slug=cat_data['slug'],
                defaults={'name': cat_data['name']}
            )
            categories.append(category)
        
        products_data = [
            {'name': 'Heladera No Frost 320L', 'price': 1500.00, 'category': categories[0], 'popularity': 0.95},
            {'name': 'Heladera Top Mount 260L', 'price': 900.00, 'category': categories[0], 'popularity': 0.8},
            {'name': 'Lavarropas Carga Frontal 8kg', 'price': 1100.00, 'category': categories[1], 'popularity': 0.9},
            {'name': 'Lavarropas Carga Superior 7kg', 'price': 750.00, 'category': categories[1], 'popularity': 0.7},
            {'name': 'Microondas 700W', 'price': 180.00, 'category': categories[2], 'popularity': 0.85},
            {'name': 'Microondas Convección 1000W', 'price': 320.00, 'category': categories[2], 'popularity': 0.6},
            {'name': 'Smart TV 50" 4K', 'price': 800.00, 'category': categories[3], 'popularity': 0.9},
            {'name': 'Smart TV 32" HD', 'price': 300.00, 'category': categories[3], 'popularity': 0.7},
            {'name': 'Cocina a Gas 4 Hornallas', 'price': 650.00, 'category': categories[4], 'popularity': 0.6},
            {'name': 'Anafe Eléctrico 2 Placas', 'price': 220.00, 'category': categories[4], 'popularity': 0.5},
            {'name': 'Aire Acondicionado Split 3000 Frig', 'price': 1200.00, 'category': categories[5], 'popularity': 0.8},
            {'name': 'Aire Portátil 2000 Frig', 'price': 420.00, 'category': categories[5], 'popularity': 0.5},
            {'name': 'Licuadora Profesional', 'price': 120.00, 'category': categories[6], 'popularity': 0.7},
            {'name': 'Plancha Vertical', 'price': 90.00, 'category': categories[6], 'popularity': 0.4},
            {'name': 'Aspiradora Robot', 'price': 450.00, 'category': categories[6], 'popularity': 0.6},
        ]
        
        # Asegurar que existan algunas marcas y garantías por defecto
        default_brands = ['Generic', 'HomeTech', 'ElectroMax', 'SmartGoods']
        for b in default_brands:
            Brand.objects.get_or_create(name=b)

        default_warranties = [
            {'name': 'Garantía Estándar 1 Año', 'duration_days': 365},
            {'name': 'Garantía Extendida 2 Años', 'duration_days': 730}
        ]
        for w in default_warranties:
            Warranty.objects.get_or_create(name=w['name'], defaults={'duration_days': w['duration_days']})

        products = []
        for i, prod_data in enumerate(products_data):
            brand = None
            warranty = None
            try:
                # Intentamos leer marcas/garantías existentes
                brands = list(Brand.objects.all())
                warranties = list(Warranty.objects.all())
                if brands:
                    brand = brands[i % len(brands)]
                if warranties:
                    warranty = warranties[i % len(warranties)]
            except Exception:
                brands = []
                warranties = []

            product, created = Product.objects.get_or_create(
                name=prod_data['name'],
                defaults={
                    'price': Decimal(str(prod_data['price'])),
                    'category': prod_data['category'],
                    'stock': random.randint(20, 200),
                    'description': f"Producto demo: {prod_data['name']}",
                    'brand': brand,
                    'warranty': warranty,
                }
            )
            # Asegurar que las métricas rating/energy existan o se actualicen
            self._ensure_product_metrics(product)
            # Guardar popularidad para uso interno (anexado dinámicamente)
            setattr(product, '_popularity', prod_data.get('popularity', 0.5))
            # Asignar imagen placeholder si no existe
            try:
                placeholder_rel = 'products/placeholder.png'
                media_placeholder = os.path.join(settings.MEDIA_ROOT, placeholder_rel)
                if not os.path.exists(media_placeholder):
                    os.makedirs(os.path.dirname(media_placeholder), exist_ok=True)
                    # Crear un PNG mínimo válido (1x1 px)
                    png_bytes = (
                        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\nIDATx\x9cc```\x00\x00\x00\x02\x00\x01\xe2!\xbc\x33\x00\x00\x00\x00IEND\xaeB`\x82"
                    )
                    with open(media_placeholder, 'wb') as f:
                        f.write(png_bytes)
                # Si no tiene imagen, asignar placeholder relativo (ImageField guarda ruta relativa)
                if not product.image:
                    product.image = placeholder_rel
                    product.save()
            except Exception:
                # No bloquear la generación si falla guardar imagen
                pass

            products.append(product)
        
        return products

    def _ensure_product_metrics(self, product: Product):
        """
        Calcula y asigna rating y energy_kwh_per_year al producto si es necesario.
        No elimina ni modifica otros campos.
        """
        updated = False
        try:
            if getattr(product, 'rating', None) is None:
                pop = getattr(product, '_popularity', None)
                if pop is None:
                    base = 3.5 + min(1.5, float(product.price) / 2000.0)
                else:
                    base = 3.5 + (0.0 if pop is None else (pop - 0.5) * 2.0)
                rating_val = max(0.0, min(5.0, round(base + random.uniform(-0.3, 0.3), 2)))
                product.rating = Decimal(str(rating_val))
                updated = True
        except Exception:
            pass

        try:
            if getattr(product, 'energy_kwh_per_year', None) is None:
                cat = getattr(product.category, 'name', '').lower() if getattr(product, 'category', None) else ''
                if 'heladera' in cat:
                    energy = random.randint(250, 550)
                elif 'lavarropas' in cat:
                    energy = random.randint(50, 200)
                elif 'microondas' in cat:
                    energy = random.randint(50, 120)
                elif 'televisor' in cat:
                    energy = random.randint(30, 200)
                elif 'aire' in cat:
                    energy = random.randint(500, 2000)
                elif 'cocina' in cat:
                    energy = random.choice([0, random.randint(200, 800)])
                else:
                    energy = random.randint(20, 500)
                product.energy_kwh_per_year = float(energy)
                updated = True
        except Exception:
            pass

        if updated:
            try:
                product.save()
            except Exception:
                pass
    
    def _create_demo_customers_if_needed(self) -> List[User]:
        """Crea clientes de demo si no existen."""
        # Verificar si ya hay clientes
        clients = list(User.objects.filter(profile__role='CLIENT')[:30])
        if len(clients) >= 15:
            return clients

        # Crear más clientes demo (hasta 30)
        customers = []
        base_names = [
            ('Juan', 'Pérez'), ('María', 'García'), ('Carlos', 'López'), ('Ana', 'Martínez'),
            ('Luis', 'Rodríguez'), ('Sofía', 'Fernández'), ('Mateo', 'Gómez'), ('Valentina', 'Díaz'),
            ('Lucas', 'Torres'), ('Camila', 'Ruiz'), ('Diego', 'Alvarez'), ('Mía', 'Sánchez'),
            ('Martín', 'Romero'), ('Lucía', 'Ramírez'), ('Tomás', 'Vega'), ('Isabella', 'Rossi'),
        ]
        idx = 1
        for first, last in base_names:
            username = f"cliente{idx}"
            email = f"{username}@demo.com"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': first,
                    'last_name': last,
                }
            )
            if created:
                try:
                    user.set_password('demo123')
                    user.save()
                except Exception:
                    pass
                # Asegurar que tenga perfil
                if not hasattr(user, 'profile'):
                    try:
                        from api.models import Profile
                        Profile.objects.create(user=user, role='CLIENT')
                    except Exception:
                        pass
            customers.append(user)
            idx += 1

        return customers
    
    def _get_seasonal_multiplier(self, date: datetime) -> float:
        """
        Calcula un multiplicador estacional basado en el mes.
        - Diciembre (12): Alto (navidad)
        - Enero-Febrero: Bajo (post navidad)
        - Julio: Alto (medio año)
        - Resto: Normal
        """
        month = date.month
        
        if month == 12:
            return 1.5  # Pico navideño
        elif month in [1, 2]:
            return 0.7  # Bajón post navidad
        elif month in [7, 8]:
            return 1.3  # Temporada media alta
        elif month in [6, 11]:
            return 1.2  # Pre-vacaciones y pre-navidad
        else:
            return 1.0  # Normal
    
    def _get_trend_multiplier(self, date: datetime) -> float:
        """
        Calcula un multiplicador de tendencia (crecimiento en el tiempo).
        Simula crecimiento del negocio.
        """
        days_from_start = (date - self.start_date).days
        total_days = (self.end_date - self.start_date).days
        progress = days_from_start / total_days
        
        # Crecimiento del 50% durante el período
        return 1.0 + (progress * 0.5)
    
    def _get_weekday_multiplier(self, date: datetime) -> float:
        """
        Calcula multiplicador según día de la semana.
        - Fin de semana: Más ventas
        - Días laborables: Ventas normales
        """
        weekday = date.weekday()
        
        if weekday in [5, 6]:  # Sábado y Domingo
            return 1.3
        elif weekday == 4:  # Viernes
            return 1.1
        else:
            return 1.0
    
    def _generate_daily_sales_count(self, date: datetime) -> int:
        """
        Calcula cuántas ventas generar para un día específico.
        """
        # Base: 5-15 ventas por día
        base_sales = random.randint(5, 15)
        
        # Aplicar multiplicadores
        seasonal = self._get_seasonal_multiplier(date)
        trend = self._get_trend_multiplier(date)
        weekday = self._get_weekday_multiplier(date)
        
        # Variabilidad aleatoria (80%-120%)
        random_factor = random.uniform(0.8, 1.2)
        
        # Calcular ventas finales
        sales_count = int(base_sales * seasonal * trend * weekday * random_factor)
        
        return max(1, sales_count)  # Mínimo 1 venta
    
    def _generate_order_items(self, products: List[Product]) -> List[Dict[str, Any]]:
        """
        Genera items para una orden, considerando popularidad de productos.
        """
        # Número de items por orden (1-4)
        num_items = random.choices([1, 2, 3, 4], weights=[0.5, 0.3, 0.15, 0.05])[0]
        
        # Seleccionar productos según popularidad
        selected_products = random.choices(
            products,
            weights=[getattr(p, '_popularity', 0.5) for p in products],
            k=num_items
        )
        
        items = []
        for product in selected_products:
            quantity = random.choices([1, 2, 3], weights=[0.7, 0.2, 0.1])[0]
            items.append({
                'product': product,
                'quantity': quantity,
                'price': product.price
            })
        
        return items
    
    @transaction.atomic
    def generate_demo_data(self, clear_existing: bool = False) -> Dict[str, Any]:
        """
        Genera datos sintéticos de ventas.
        
        Args:
            clear_existing: Si es True, elimina las órdenes existentes antes de generar
            
        Returns:
            Dict con estadísticas de generación
        """
        if clear_existing:
            Order.objects.all().delete()
            print("✓ Órdenes existentes eliminadas")
        
        # Preparar datos
        products = self._create_demo_products_if_needed()
        customers = self._create_demo_customers_if_needed()
        
        print(f"✓ Usando {len(products)} productos y {len(customers)} clientes")
        
        # Generar ventas día por día
        current_date = self.start_date
        total_orders = 0
        total_revenue = Decimal('0.00')
        
        while current_date <= self.end_date:
            daily_sales = self._generate_daily_sales_count(current_date)
            
            for _ in range(daily_sales):
                # Seleccionar cliente aleatorio
                customer = random.choice(customers)
                
                # Generar items
                items_data = self._generate_order_items(products)
                
                # Calcular total
                order_total = sum(
                    Decimal(str(item['quantity'])) * item['price'] 
                    for item in items_data
                )
                
                # Fecha específica para esta orden
                order_date = current_date + timedelta(
                    hours=random.randint(8, 20),
                    minutes=random.randint(0, 59)
                )
                
                # Crear orden (auto_now_add pone la fecha actual, la actualizaremos después)
                try:
                    # Usar un savepoint anidado para que errores puntuales no rompan la transacción global
                    with transaction.atomic():
                        order = Order.objects.create(
                            customer=customer,
                            total_price=order_total,
                            status='COMPLETED'
                        )
                except DatabaseError as e:
                    # Si la tabla aún no tiene todas las columnas (migración en curso), saltar esta orden
                    print(f"❌ ERROR creando Order: {e}")
                    continue
                except Exception as e:
                    print(f"❌ ERROR inesperado creando Order: {e}")
                    continue
                
                # Actualizar la fecha manualmente (by-passing auto_now_add)
                Order.objects.filter(pk=order.pk).update(
                    created_at=order_date,
                    updated_at=order_date
                )
                
                # Crear items de la orden
                for item_data in items_data:
                    try:
                        with transaction.atomic():
                            OrderItem.objects.create(
                                order=order,
                                product=item_data['product'],
                                quantity=item_data['quantity'],
                                price=item_data['price']
                            )
                        # Reducir stock de producto (si existe)
                        try:
                            p = item_data['product']
                            if hasattr(p, 'stock') and p.stock >= item_data['quantity']:
                                p.stock = max(0, p.stock - item_data['quantity'])
                                p.save()
                        except Exception:
                            pass
                    except Exception as e:
                        print(f"❌ ERROR creando OrderItem: {e}")
                        # No abortar toda la generación
                        continue
                
                total_orders += 1
                total_revenue += order_total
            
            current_date += timedelta(days=1)
        
        print(f"✓ Generadas {total_orders} órdenes")
        print(f"✓ Ingresos totales: ${total_revenue:,.2f}")
        
        return {
            'total_orders': total_orders,
            'total_revenue': float(total_revenue),
            'start_date': self.start_date.strftime('%Y-%m-%d'),
            'end_date': self.end_date.strftime('%Y-%m-%d'),
            'products_count': len(products),
            'customers_count': len(customers)
        }


def generate_sales_data(clear_existing: bool = False) -> Dict[str, Any]:
    """
    Función helper para generar datos de ventas demo.
    
    Args:
        clear_existing: Si es True, elimina las órdenes existentes antes de generar
        
    Returns:
        Dict con estadísticas de generación
        
    Ejemplo:
        >>> from sales.ml_data_generator import generate_sales_data
        >>> stats = generate_sales_data(clear_existing=True)
        >>> print(stats)
    """
    generator = SalesDataGenerator()
    return generator.generate_demo_data(clear_existing=clear_existing)


def update_products_metrics(limit: int = 0) -> Dict[str, int]:
    """
    Helper de módulo para actualizar métricas de productos (rating, energy_kwh_per_year).
    Útil para ejecutar desde manage.py shell: from sales.ml_data_generator import update_products_metrics; update_products_metrics()
    """
    products = list(Product.objects.all())
    checked = 0
    updated = 0
    gen = SalesDataGenerator()
    for p in products:
        if limit and checked >= limit:
            break
        before_rating = getattr(p, 'rating', None)
        before_energy = getattr(p, 'energy_kwh_per_year', None)
        gen._ensure_product_metrics(p)
        checked += 1
        if getattr(p, 'rating', None) != before_rating or getattr(p, 'energy_kwh_per_year', None) != before_energy:
            updated += 1

    return {'products_checked': checked, 'products_updated': updated}
