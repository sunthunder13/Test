# Generated by Django 5.2.1 on 2025-05-24 13:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0007_remove_inventory_product_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='inventory',
            name='retail_price',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
