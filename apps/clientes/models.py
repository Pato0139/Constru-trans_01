from django.db import models
class Cliente(models.Model):
    usuario = models.OneToOneField('usuarios.Usuario', on_delete=models.CASCADE, related_name='perfil_cliente')
    nit_rut = models.CharField(max_length=20, unique=True, null=True, blank=True)
    razon_social = models.CharField(max_length=200, null=True, blank=True)
    direccion_fiscal = models.TextField(null=True, blank=True)
    ciudad = models.CharField(max_length=100, null=True, blank=True)
    telefono_contacto = models.CharField(max_length=20, null=True, blank=True)
    email_empresa = models.EmailField(null=True, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.usuario.nombres} {self.usuario.apellidos}"

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender='usuarios.Usuario')
def crear_perfil_cliente(sender, instance, created, **kwargs):
    if created and instance.rol == 'cliente':
        Cliente.objects.get_or_create(usuario=instance)