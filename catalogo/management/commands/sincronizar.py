import os
import time

from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import OperationalError, connections

from clientes.models import Cliente
from compras.models import Compra
from auditoria.models import Historial
from catalogo.models import MovimientoInventario
from pedidos.models import Orden
from logistica.models import Entrega
from catalogo.models import MaterialConstruccion as Material
from compras.models import Proveedor
from usuarios.models import Usuario
from logistica.models import Vehiculo


def conexion_remota_disponible():
    try:
        from django.db.utils import ConnectionDoesNotExist

        if "remota" not in connections:
            return False
        if not os.getenv("DB_ENGINE") or not os.getenv("DB_PASSWORD"):
            return False
        connections["remota"].ensure_connection()
        return True
    except (OperationalError, ConnectionDoesNotExist, Exception):
        return False


class Command(BaseCommand):
    help = "Sincroniza los datos locales pendientes con la base de datos remota (Neon)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--once",
            action="store_true",
            help="Ejecuta la sincronización una sola vez y termina",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Sincroniza todos los registros, ignorando el estado de sincronización actual",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("--- Iniciando Sincronizador (El Celador) ---"))

        force = options.get("force", False)
        if force:
            self.stdout.write(
                self.style.WARNING("MODO FORZADO: Se sincronizarán todos los registros.")
            )

        while True:
            try:
                if not conexion_remota_disponible():
                    self.stdout.write(
                        self.style.WARNING(
                            "Sin conexión con la nube. Reintentando en 30 segundos..."
                        )
                    )
                else:
                    self.stdout.write(self.style.SUCCESS("Conexión con la nube establecida."))

                    self.descargar_usuarios()
                    self.sincronizar_grupos(force=force)
                    self.sincronizar_usuarios(force=force)
                    self.sincronizar_modelo(Proveedor, force=force)
                    self.sincronizar_modelo(Material, force=force)
                    self.sincronizar_modelo(Vehiculo, force=force)
                    self.sincronizar_modelo(Compra, force=force)
                    self.sincronizar_modelo(Orden, force=force)
                    self.sincronizar_modelo(Entrega, force=force)
                    self.sincronizar_modelo(MovimientoInventario, force=force)
                    self.sincronizar_modelo(Historial, force=force)
                    self.sincronizar_log_admin()

                    self.corregir_secuencias_remotas()

            except OperationalError:
                self.stdout.write(
                    self.style.WARNING("Sin conexión con la nube. Reintentando en 30 segundos...")
                )

            if options["once"]:
                self.stdout.write(self.style.SUCCESS("Sincronización única completada."))
                break

            time.sleep(30)

    def sincronizar_grupos(self, force=False):
        try:
            self.stdout.write("Sincronizando Grupos y Permisos...")
            grupos = Group.objects.using("default").all()
            for group in grupos:
                Group.objects.using("remota").update_or_create(
                    id=group.id, defaults={"name": group.name}
                )

            users = User.objects.using("default").all()
            for user in users:
                user_remoto = User.objects.using("remota").filter(id=user.id).first()
                if user_remoto:
                    grupos_ids = list(user.groups.values_list("id", flat=True))
                    user_remoto.groups.set(Group.objects.using("remota").filter(id__in=grupos_ids))

            self.stdout.write(self.style.SUCCESS("  [OK] Grupos y relaciones sincronizados."))
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"  [ERROR] Falló sincronización de Grupos: {str(e)}")
            )

    def sincronizar_modelo(self, modelo, force=False):
        pk_field = modelo._meta.pk
        pk_name = pk_field.name

        if force:
            pendientes = modelo.objects.using("default").all().order_by(pk_name)
        else:
            pendientes = (
                modelo.objects.using("default").filter(sincronizado=False).order_by(pk_name)
            )

        if pendientes.exists():
            self.stdout.write(
                f"Sincronizando {pendientes.count()} registros de {modelo.__name__}..."
            )
            for obj in pendientes:
                try:
                    data = {}
                    for field in obj._meta.fields:
                        if field.name != "sincronizado" and not field.primary_key:
                            if field.is_relation and field.many_to_one:
                                data[field.name + "_id"] = getattr(obj, field.name + "_id")
                            else:
                                data[field.name] = getattr(obj, field.name)

                    modelo.objects.using("remota").update_or_create(
                        **{pk_name: getattr(obj, pk_name)}, defaults=data
                    )

                    for rel in obj._meta.related_objects:
                        if rel.get_accessor_name() == "detalles":
                            detalles = obj.detalles.all().order_by("id")
                            for detalle in detalles:
                                d_data = {}
                                for d_field in detalle._meta.fields:
                                    if d_field.is_relation and d_field.many_to_one:
                                        d_data[d_field.name + "_id"] = getattr(
                                            detalle, d_field.name + "_id"
                                        )
                                    else:
                                        d_data[d_field.name] = getattr(detalle, d_field.name)

                                detalle.__class__.objects.using("remota").update_or_create(
                                    id=detalle.id, defaults=d_data
                                )

                    obj.sincronizado = True
                    obj.save(using="default")
                    self.stdout.write(
                        self.style.SUCCESS(f"  [OK] {obj} y sus detalles sincronizados.")
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"  [ERROR] Falló sincronización de {obj}: {str(e)}")
                    )

    def sincronizar_log_admin(self):
        try:
            ultimo_id_remoto = LogEntry.objects.using("remota").order_by("-id").first()
            ultimo_id = ultimo_id_remoto.id if ultimo_id_remoto else 0

            pendientes = LogEntry.objects.using("default").filter(id__gt=ultimo_id).order_by("id")

            if pendientes.exists():
                self.stdout.write(f"Sincronizando {pendientes.count()} logs de Django Admin...")
                for log in pendientes:
                    data = {}
                    for field in log._meta.fields:
                        if field.is_relation and field.many_to_one:
                            data[field.name + "_id"] = getattr(log, field.name + "_id")
                        else:
                            data[field.name] = getattr(log, field.name)

                    LogEntry.objects.using("remota").update_or_create(id=log.id, defaults=data)
                self.stdout.write(
                    self.style.SUCCESS(f"  [OK] {pendientes.count()} logs sincronizados.")
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"  [ERROR] Falló sincronización de LogEntry: {str(e)}")
            )

    def sincronizar_usuarios(self, force=False):
        if force:
            usuarios_pendientes = Usuario.objects.using("default").all().order_by("id")
        else:
            usuarios_pendientes = (
                Usuario.objects.using("default").filter(sincronizado=False).order_by("id")
            )
            self.stdout.write(f"Sincronizando {usuarios_pendientes.count()} usuarios...")
            for perfil in usuarios_pendientes:
                try:
                    user_django = perfil.user
                    u_data = {}
                    for field in user_django._meta.fields:
                        u_data[field.name] = getattr(user_django, field.name)

                    User.objects.using("remota").update_or_create(
                        id=user_django.id, defaults=u_data
                    )

                    p_data = {}
                    for field in perfil._meta.fields:
                        if field.name != "sincronizado":
                            p_data[field.name] = getattr(perfil, field.name)

                    Usuario.objects.using("remota").update_or_create(id=perfil.id, defaults=p_data)

                    if perfil.rol == "cliente":
                        try:
                            cliente_perfil = Cliente.objects.using("default").get(usuario=perfil)
                            c_data = {}
                            for field in cliente_perfil._meta.fields:
                                if not field.primary_key:
                                    c_data[field.name] = getattr(cliente_perfil, field.name)

                            Cliente.objects.using("remota").update_or_create(
                                usuario=perfil, defaults=c_data
                            )
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"    [OK] Perfil de Cliente sincronizado para {perfil.user.username}"
                                )
                            )
                        except Cliente.DoesNotExist:
                            pass

                    perfil.sincronizado = True
                    perfil.save(using="default")
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  [OK] Usuario {perfil.user.username} y sus perfiles sincronizados."
                        )
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"  [ERROR] Falló sincronización de usuario {perfil}: {e}")
                    )

    def descargar_usuarios(self):
        try:
            self.stdout.write("Descargando datos base desde la nube...")

            usuarios_remotos = User.objects.using("remota").all()
            for u_remoto in usuarios_remotos:
                User.objects.using("default").update_or_create(
                    id=u_remoto.id,
                    defaults={
                        "username": u_remoto.username,
                        "password": u_remoto.password,
                        "email": u_remoto.email,
                        "first_name": u_remoto.first_name,
                        "last_name": u_remoto.last_name,
                        "is_staff": u_remoto.is_staff,
                        "is_active": u_remoto.is_active,
                        "is_superuser": u_remoto.is_superuser,
                        "last_login": u_remoto.last_login,
                        "date_joined": u_remoto.date_joined,
                    },
                )
                p_remoto = Usuario.objects.using("remota").filter(user_id=u_remoto.id).first()
                if p_remoto:
                    Usuario.objects.using("default").update_or_create(
                        id=p_remoto.id,
                        defaults={
                            "user_id": u_remoto.id,
                            "rol": p_remoto.rol,
                            "telefono": p_remoto.telefono,
                            "sincronizado": True,
                        },
                    )

            for p in Proveedor.objects.using("remota").all():
                Proveedor.objects.using("default").update_or_create(
                    codigo_proveedor=p.codigo_proveedor,
                    defaults={
                        "nombre_empresa": p.nombre_empresa,
                        "nit": p.nit,
                        "telefono": p.telefono,
                        "correo": getattr(p, "correo", ""),
                        "descripcion": getattr(p, "descripcion", ""),
                        "sincronizado": True,
                    },
                )

            for m in Material.objects.using("remota").all():
                Material.objects.using("default").update_or_create(
                    id=m.id,
                    defaults={
                        "nombre": m.nombre,
                        "descripcion": m.descripcion,
                        "precio": m.precio,
                        "sincronizado": True,
                    },
                )

            for v in Vehiculo.objects.using("remota").all():
                Vehiculo.objects.using("default").update_or_create(
                    id_vehiculo=v.id_vehiculo,
                    defaults={
                        "placa": v.placa,
                        "marca": v.marca,
                        "modelo": v.modelo,
                        "capacidad_carga": v.capacidad_carga,
                        "estado": v.estado,
                        "sincronizado": True,
                    },
                )

            self.stdout.write(self.style.SUCCESS("  [OK] Usuarios actualizados desde la nube."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  [ERROR] Falló la descarga de datos: {str(e)}"))

    def corregir_secuencias_remotas(self):
        try:
            self.stdout.write("Corrigiendo secuencias en la nube...")
            with connections["remota"].cursor() as cursor:
                tablas = [
                    ("auth_user", "id"),
                    ("usuario", "id_usuario"),
                    ("material_construccion", "id_material"),
                    ("vehiculo", "id_vehiculo"),
                    ("proveedor", "codigo_proveedor"),
                    ("pedido", "codigo_pedido"),
                    ("historial_actividad", "id_historial"),
                ]
                for tabla, columna in tablas:
                    try:
                        sql = f"SELECT setval(pg_get_serial_sequence('{tabla}', '{columna}'), (SELECT MAX({columna}) FROM {tabla}));"
                        cursor.execute(sql)
                    except Exception:
                        continue
            self.stdout.write(self.style.SUCCESS("  [OK] Secuencias de la nube corregidas."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  [ERROR] Falló corregir secuencias: {str(e)}"))
