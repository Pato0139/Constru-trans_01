from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Usuario, Material, Stock

@receiver(post_save, sender=Material)
def create_material_stock(sender, instance, created, **kwargs):
    """Crea un registro de Stock cuando se crea un nuevo Material"""
    if created:
        Stock.objects.get_or_create(material=instance)

# Aquí puedes agregar señales para el modelo Usuario
