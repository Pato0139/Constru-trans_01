from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.gestion_pedidos.models import DetallePedido, Pedido
from apps.usuarios.models import Catalogo, MaterialConstruccion, UnidadMedida, Usuario


class Command(BaseCommand):
    help = "Llena datos de prueba: teléfonos, tipos de materiales y pedidos"
    DB_ALIAS = "default"

    def handle(self, *args, **kwargs):
        self.stdout.write("=" * 40)
        self.stdout.write("  LLENANDO DATOS DE PRUEBA")
        self.stdout.write("=" * 40)

        self.llenar_telefonos_clientes()
        self.llenar_tipos_materiales()
        self.crear_pedidos_y_ventas()

        self.stdout.write("\nDATOS DE PRUEBA LLENADOS CORRECTAMENTE!")

    def llenar_telefonos_clientes(self):
        """Llenar teléfonos a clientes específicos"""
        self.stdout.write("\n--- Llenando teléfonos de clientes ---")
        # First, let's get ALL usuarios to see what's there!
        self.stdout.write("  Usuarios disponibles en la BD:")
        for u in Usuario.objects.using(self.DB_ALIAS).all()[:20]:
            self.stdout.write(f"    - {u.id}: {u.nombres} {u.apellidos}")

        datos = [
            ("Cliente Nombres 2 Apellidos 2", "3001234567"),
            ("Cliente Nombres 3 Apellidos 3", "3012345678"),
            ("Cliente Nombres 4 Apellidos 4", "3023456789"),
            ("Cliente Nombres 5 Apellidos 5", "3034567890"),
            ("Cliente Frecuente", "3045678901"),
            ("Ing. Roberto Torres", "3056789012"),
            ("Lucia Perez", "3107890123"),
            ("Andres Rodriguez", "3118901234"),
        ]

        for nombre_completo, telefono in datos:
            try:
                # Buscar el usuario
                usuarios = Usuario.objects.using(self.DB_ALIAS).filter(
                    nombres__icontains=nombre_completo
                )
                if not usuarios:
                    # Try just nombres only
                    usuarios = Usuario.objects.using(self.DB_ALIAS).filter(
                        nombres__icontains=" ".join(nombre_completo.split()[:2])
                    )

                if usuarios:
                    usuario = usuarios.first()
                    usuario.telefono = telefono
                    usuario.save(using=self.DB_ALIAS)
                    self.stdout.write(f"[OK] {usuario.nombres} {usuario.apellidos} : {telefono}")
                else:
                    pass  # Skip
            except Exception:
                pass

        # Also, let's just fill some random clientes!
        self.stdout.write("\n  Llenando telefonos a clientes aleatorios:")
        clientes = Usuario.objects.using(self.DB_ALIAS).filter(rol="cliente")
        telefonos = [
            "3001234567",
            "3012345678",
            "3023456789",
            "3034567890",
            "3045678901",
            "3056789012",
            "3107890123",
            "3118901234",
        ]
        for i, c in enumerate(clientes[:8]):
            c.telefono = telefonos[i % len(telefonos)]
            c.save(using=self.DB_ALIAS)
            self.stdout.write(f"[OK] {c.nombres} {c.apellidos} : {c.telefono}")

    def llenar_tipos_materiales(self):
        """Llenar tipos (Catalogo) y materiales de prueba"""
        self.stdout.write("\n--- Llenando tipos y materiales de prueba ---")

        # Asegurar que los catalogos existan
        tipos = [
            ("CEM", "Cementos y Hormigon"),
            ("MET", "Metales y Acero"),
            ("GEN", "Materiales Generales"),
            ("ARE", "Arenas y Grava"),
        ]

        for codigo, nombre in tipos:
            Catalogo.objects.using(self.DB_ALIAS).get_or_create(
                codigo_catalogo=codigo, defaults={"nombre_empresa": nombre}
            )
            self.stdout.write(f"[OK] Catalogo: {nombre}")

        # Get unidad de medida!
        try:
            unidad, _ = UnidadMedida.objects.using(self.DB_ALIAS).get_or_create(
                codigo="UN", defaults={"nombre": "Unidad", "abreviatura": "un"}
            )
        except:
            # If UnidadMedida doesn't exist, we might need to skip, but let's try to get any!
            unidad = UnidadMedida.objects.using(self.DB_ALIAS).first()
            if not unidad:
                self.stdout.write("[ERROR] No hay unidades de medida disponibles!")
                return

        # Crear materiales de prueba!
        materiales_datos = [
            ("Cemento Gris Argos 50kg", "Cementos y Hormigon", 57000.00, unidad),
            ('Varilla Corrugada 1/2"', "Metales y Acero", 28000.00, unidad),
            ("Ladrillo Estructural", "Materiales Generales", 1200.00, unidad),
            ("Arena de Rio (m3)", "Arenas y Grava", 85000.00, unidad),
            ("Grava 3/4 (m3)", "Arenas y Grava", 92000.00, unidad),
        ]

        for nombre_material, nombre_tipo, precio, unidad in materiales_datos:
            try:
                catalogo = (
                    Catalogo.objects.using(self.DB_ALIAS).filter(nombre_empresa=nombre_tipo).first()
                )
                # Get or create material!
                material, created = MaterialConstruccion.objects.using(self.DB_ALIAS).get_or_create(
                    nombre=nombre_material,
                    defaults={
                        "catalogo": catalogo,
                        "unidad_medida": unidad,
                        "descripcion": f"{nombre_material} de prueba",
                        "precio_referencia": precio,
                    },
                )
                if created:
                    self.stdout.write(
                        f"[OK] Creado material: {material.nombre} : {catalogo.nombre_empresa}"
                    )
                else:
                    # Update catalogo if missing
                    if not material.catalogo and catalogo:
                        material.catalogo = catalogo
                        material.save(using=self.DB_ALIAS)
                        self.stdout.write(f"[OK] Actualizado catalogo de: {material.nombre}")
            except Exception as e:
                self.stdout.write(f"[ERROR] {e}")

        # Also, fill any remaining materiales with catalogo!
        self.stdout.write("\n  Llenando tipos a materiales aleatorios:")
        catalogos = Catalogo.objects.using(self.DB_ALIAS).all()
        for m in MaterialConstruccion.objects.using(self.DB_ALIAS).filter(catalogo__isnull=True):
            if catalogos:
                m.catalogo = catalogos[m.id % len(catalogos)]
                m.save(using=self.DB_ALIAS)
                self.stdout.write(f"[OK] {m.nombre} : {m.catalogo.nombre_empresa}")

    def crear_pedidos_y_ventas(self):
        """Crear pedidos y datos de ventas de ejemplo"""
        self.stdout.write("\n--- Creando pedidos y ventas ---")

        # Get actual clientes and materials from DB!
        clientes = list(Usuario.objects.using(self.DB_ALIAS).filter(rol="cliente")[:5])
        materiales = list(MaterialConstruccion.objects.using(self.DB_ALIAS).all()[:5])

        self.stdout.write(f"  Clientes encontrados: {len(clientes)}")
        self.stdout.write(f"  Materiales encontrados: {len(materiales)}")
        for m in materiales:
            self.stdout.write(f"    - {m.nombre}")

        if not clientes or not materiales:
            self.stdout.write("[AVISO] No hay suficientes clientes o materiales para crear pedidos")
            return

        # Create sample pedidos
        estados = ["pendiente", "aprobado", "entregado", "cancelado"]

        for i in range(7):
            try:
                cliente = clientes[i % len(clientes)]
                material = materiales[i % len(materiales)]
                estado = estados[i % len(estados)]

                # Parsear fecha
                fecha = timezone.make_aware(
                    timezone.datetime(2026, 6, 17) - timezone.timedelta(days=i)
                )

                # Calcular total
                cantidad = (i % 5) + 1
                total = cantidad * material.precio_referencia

                # Crear pedido
                pedido = Pedido.objects.using(self.DB_ALIAS).create(
                    cliente=cliente,
                    fecha_creacion=fecha,
                    estado=estado,
                    total=total,
                    descuento=0,
                )

                # Crear detalle
                DetallePedido.objects.using(self.DB_ALIAS).create(
                    pedido=pedido,
                    material=material,
                    cantidad=cantidad,
                    precio_unitario=material.precio_referencia,
                )

                self.stdout.write(
                    f"[OK] Pedido #{pedido.id} : Cliente {cliente.id}, Estado: {estado}, Total: ${total}"
                )
            except Exception as e:
                self.stdout.write(f"[ERROR] Error creando pedido: {e}")
