from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0004_offer'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='rating',
            field=models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='product',
            name='energy_kwh_per_year',
            field=models.FloatField(null=True, blank=True),
        ),
    ]
