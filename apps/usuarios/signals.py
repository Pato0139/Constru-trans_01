from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Usuario, Material, StockMaterial

@receiver(post_save, sender=Material)
def crear_stock_material(sender, instance, created, **kwargs):
    if created:
        StockMaterial.objects.get_or_create(material=instance)

# Aquí puedes agregar señales para el modelo Usuario
