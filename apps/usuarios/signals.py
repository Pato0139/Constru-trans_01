from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Usuario


@receiver(post_save, sender=User)
def crear_usuario_perfil(sender, instance, created, **kwargs):
    if created:
        from apps.usuarios.models import Rol
        rol_default, _ = Rol.objects.get_or_create(nombre_rol='empleado')
        Usuario.objects.get_or_create(
            user=instance,
            defaults={
                'nombre': instance.username,
                'correo': instance.email if instance.email else f"{instance.username}@ejemplo.com",
                'documento': '00000000',
                'tipo_documento': 'CC',
                'rol': rol_default
            }
        )
