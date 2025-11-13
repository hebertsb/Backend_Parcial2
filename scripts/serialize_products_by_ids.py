import os
import sys
import json
from pathlib import Path

# Ensure project root is on sys.path so Django can import 'backend'
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from products.models import Product
from products.serializers import ProductSerializer

def serialize_ids(ids):
    qs = Product.objects.filter(id__in=ids)
    serializer = ProductSerializer(qs, many=True, context={'request': None})
    return serializer.data

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Uso: python serialize_products_by_ids.py 1 2 3')
        print('  o: python serialize_products_by_ids.py list  # listar primeros productos disponibles')
        sys.exit(1)

    if sys.argv[1] == 'list':
        from products.models import Product
        qs = Product.objects.all()[:10]
        out = [{'id': p.id, 'name': p.name} for p in qs]
        print(json.dumps(out, indent=2, ensure_ascii=False))
        sys.exit(0)

    try:
        ids = [int(x) for x in sys.argv[1:]]
    except ValueError:
        print('Los IDs deben ser enteros')
        sys.exit(1)
    data = serialize_ids(ids)
    print(json.dumps(data, indent=2, ensure_ascii=False))
