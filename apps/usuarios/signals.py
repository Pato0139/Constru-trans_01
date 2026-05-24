from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Usuario


@receiver(post_save, sender=User)
def crear_usuario_perfil(sender, instance, created, **kwargs):
    if created:
        Usuario.objects.get_or_create(
            user=instance,
            defaults={
                'nombres': instance.first_name or instance.username,
                'apellidos': instance.last_name or '',
                'telefono': '',
                'documento': '00000000',
                'tipo_documento': 'CC',
                'rol': 'empleado',
                'estado': 'activo'
            }
        )
