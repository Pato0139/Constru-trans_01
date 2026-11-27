"""
Sincronización y replicación Remota (Neon) -> Local (SQLite).

Provee:
  - MODELOS_SINCRONIZABLES: orden estricto de dependencias FK para clonar sin errores.
  - sincronizar_remota_a_local(): descarga/actualiza todos los registros de 'remota' en 'local'.
  - replicar_instancia_a_local() / eliminar_instancia_en_local(): replicación en tiempo real
    usada por las señales post_save / post_delete cuando se trabaja en modo remoto.
"""

import logging
import os
import sys
import threading
import time

from django.apps import apps
from django.conf import settings
from django.db import connections
from django.db.models import Count, Max

logger = logging.getLogger(__name__)

_sync_state = threading.local()
_celador_lock = threading.Lock()
_celador_started = False

# Orden topológico respetando llaves foráneas (padres primero, hijos después)
MODELOS_SINCRONIZABLES = (
    # 1. Seguridad, usuarios y perfiles
    "usuarios.Rol",
    "usuarios.Permiso",
    "usuarios.RolPermiso",
    "usuarios.EPS",
    "usuarios.Usuario",
    "usuarios.UsuarioRol",
    "usuarios.PermisoUsuario",
    "usuarios.Conductor",
    "usuarios.Notificacion",
    # 2. Clientes
    "clientes.Cliente",
    # 3. Catálogo e inventario
    "catalogo.Catalogo",
    "catalogo.UnidadMedida",
    "catalogo.Marca",
    "catalogo.MaterialConstruccion",
    "catalogo.Stock",
    "catalogo.MovimientoInventario",
    # 4. Compras y proveedores
    "compras.Proveedor",
    "compras.ProveedorMaterial",
    "compras.Compra",
    "compras.DetalleCompra",
    # 5. Flota y asignaciones
    "logistica.Vehiculo",
    "logistica.ConductorVehiculo",
    # 6. Pedidos
    "pedidos.Pedido",
    "pedidos.DetallePedido",
    # 7. Pagos y facturación
    "pagos.Pago",
    "pagos.DetallePago",
    "pagos.Factura",
    # 8. Entregas y novedades
    "logistica.Entrega",
    "logistica.Novedad",
    "logistica.Seguimiento",
    "logistica.RespuestaSeguimiento",
    # 9. Consecutivos, auditoría y licenciamiento
    "core.Consecutivo",
    "auditoria.Historial",
    "licensing.Licencia",
    "licensing.UsuarioLicencia",
    "licensing.AuditoriaLicencia",
)


def esta_sincronizando() -> bool:
    return bool(getattr(_sync_state, "running", False))


def _concrete_field_values(instance) -> dict:
    """Extrae los valores crudos de columnas (attname) sin disparar queries de FK."""
    return {
        field.attname: getattr(instance, field.attname)
        for field in instance._meta.concrete_fields
    }


def _resolver_modelos():
    modelos = []
    for label in MODELOS_SINCRONIZABLES:
        try:
            modelos.append(apps.get_model(label))
        except LookupError:
            logger.debug("Modelo %s no encontrado; omitido de sincronización.", label)
    return modelos


def replicar_instancia_a_local(instance) -> bool:
    """Replica un registro guardado en 'remota' hacia 'local' (SQLite)."""
    if esta_sincronizando() or "local" not in settings.DATABASES:
        return False

    model = instance.__class__
    if model._meta.label not in MODELOS_SINCRONIZABLES:
        return False

    pk_field = model._meta.pk.attname
    pk_value = getattr(instance, pk_field, None)
    if pk_value is None:
        return False

    valores = _concrete_field_values(instance)
    defaults = {k: v for k, v in valores.items() if k != pk_field}

    _sync_state.running = True
    try:
        model.objects.using("local").update_or_create(**{pk_field: pk_value}, defaults=defaults)
        return True
    except Exception as exc:
        logger.debug(
            "No se pudo replicar %s(%s) a local: %s",
            model._meta.label,
            pk_value,
            exc,
        )
        return False
    finally:
        _sync_state.running = False


def replicar_instancia_a_remota(instance) -> bool:
    """Replica en tiempo real un registro guardado en 'local'/'default' hacia 'remota' (Neon)."""
    if esta_sincronizando() or getattr(settings, "OFFLINE_MODE", False):
        return False
    if "remota" not in settings.DATABASES:
        return False

    model = instance.__class__
    if model._meta.label not in MODELOS_SINCRONIZABLES:
        return False

    from config.utils import conexion_remota_disponible

    if not conexion_remota_disponible():
        return False

    pk_field = model._meta.pk.attname
    pk_value = getattr(instance, pk_field, None)
    if pk_value is None:
        return False

    valores = _concrete_field_values(instance)
    if "sincronizado" in valores:
        valores["sincronizado"] = True
    defaults = {k: v for k, v in valores.items() if k != pk_field}

    _sync_state.running = True
    try:
        model._base_manager.using("remota").update_or_create(
            **{pk_field: pk_value},
            defaults=defaults,
        )
        if "sincronizado" in valores:
            try:
                model._base_manager.using("local").filter(**{pk_field: pk_value}).update(sincronizado=True)
            except Exception:
                pass
        return True
    except Exception as exc:
        logger.debug(
            "No se pudo replicar %s(%s) a remota: %s",
            model._meta.label,
            pk_value,
            exc,
        )
        return False
    finally:
        _sync_state.running = False


def sincronizar_pendientes_local_a_remota() -> dict:
    """
    Sube hacia Neon ('remota') cualquier registro creado/modificado en 'local' que aún no esté
    en la nube (por ejemplo, pedidos hechos en modo offline o notificaciones locales).
    """
    if getattr(settings, "OFFLINE_MODE", False):
        return {"tablas_subidas": 0, "registros_subidos": 0}
    if "remota" not in settings.DATABASES or "local" not in settings.DATABASES:
        return {"tablas_subidas": 0, "registros_subidos": 0}

    from config.utils import conexion_remota_disponible

    if not conexion_remota_disponible():
        return {"tablas_subidas": 0, "registros_subidos": 0}

    tablas_subidas = 0
    registros_subidos = 0

    _sync_state.running = True
    try:
        for model in _resolver_modelos():
            pk_field = model._meta.pk.attname
            field_names = {f.name for f in model._meta.concrete_fields}
            has_sync_flag = "sincronizado" in field_names

            try:
                if has_sync_flag:
                    pendientes = list(
                        model._base_manager.using("local").filter(sincronizado=False).order_by(pk_field)[:100]
                    )
                else:
                    rem_max = model._base_manager.using("remota").aggregate(m=Max("pk")).get("m")
                    if rem_max is not None:
                        pendientes = list(
                            model._base_manager.using("local")
                            .filter(**{f"{pk_field}__gt": rem_max})
                            .order_by(pk_field)[:100]
                        )
                    else:
                        pendientes = []
            except Exception as exc:
                logger.debug("Celador omitió subida de %s: %s", model._meta.label, exc)
                continue

            if not pendientes:
                continue

            subidos_tabla = 0
            for obj in pendientes:
                pk_val = getattr(obj, pk_field, None)
                if pk_val is None:
                    continue
                valores = _concrete_field_values(obj)
                if has_sync_flag:
                    valores["sincronizado"] = True
                defaults = {k: v for k, v in valores.items() if k != pk_field}
                try:
                    model._base_manager.using("remota").update_or_create(
                        **{pk_field: pk_val},
                        defaults=defaults,
                    )
                    if has_sync_flag:
                        model._base_manager.using("local").filter(**{pk_field: pk_val}).update(sincronizado=True)
                    subidos_tabla += 1
                except Exception as exc:
                    logger.debug("Celador no pudo subir %s(%s): %s", model._meta.label, pk_val, exc)

            if subidos_tabla:
                tablas_subidas += 1
                registros_subidos += subidos_tabla
    finally:
        _sync_state.running = False

    return {"tablas_subidas": tablas_subidas, "registros_subidos": registros_subidos}


def eliminar_instancia_en_local(instance) -> bool:
    """Replica la eliminación de un registro de 'remota' en 'local' (SQLite)."""
    if esta_sincronizando() or "local" not in settings.DATABASES:
        return False

    model = instance.__class__
    if model._meta.label not in MODELOS_SINCRONIZABLES:
        return False

    pk_field = model._meta.pk.attname
    pk_value = getattr(instance, pk_field, None)
    if pk_value is None:
        return False

    _sync_state.running = True
    try:
        model.objects.using("local").filter(**{pk_field: pk_value}).delete()
        return True
    except Exception as exc:
        logger.debug(
            "No se pudo eliminar %s(%s) en local: %s",
            model._meta.label,
            pk_value,
            exc,
        )
        return False
    finally:
        _sync_state.running = False


def sincronizar_remota_a_local() -> list[dict]:
    """
    Descarga todos los registros de 'remota' (Neon) y los inserta/actualiza en 'local' (SQLite).
    Devuelve una lista con el resumen por modelo: [{"modelo", "remotos", "sincronizados", "errores"}].
    """
    if "remota" not in settings.DATABASES or "local" not in settings.DATABASES:
        raise RuntimeError("Se requieren las bases 'remota' y 'local' configuradas.")

    resumen = []
    local_conn = connections["local"]

    _sync_state.running = True
    try:
        # En SQLite desactivamos temporalmente foreign_keys durante la copia masiva
        # para tolerar posibles filas legacy sin bloquear el resto de tablas.
        is_sqlite = local_conn.vendor == "sqlite"
        if is_sqlite:
            with local_conn.cursor() as cursor:
                cursor.execute("PRAGMA foreign_keys = OFF;")

        try:
            for model in _resolver_modelos():
                pk_field = model._meta.pk.attname
                remotos = list(model._base_manager.using("remota").all())
                ok_count = 0
                err_count = 0
                update_fields = [
                    f.attname for f in model._meta.concrete_fields if f.attname != pk_field
                ]

                for obj in remotos:
                    valores = _concrete_field_values(obj)
                    pk_val = valores.get(pk_field)
                    try:
                        # bulk_create con update_conflicts evita full_clean() en save()
                        # personalizados sobre filas legacy y respeta los PKs exactos.
                        clon = model(**valores)
                        model._base_manager.using("local").bulk_create(
                            [clon],
                            update_conflicts=bool(update_fields),
                            unique_fields=[pk_field] if update_fields else None,
                            update_fields=update_fields or None,
                        )
                        ok_count += 1
                    except Exception as exc:
                        err_count += 1
                        logger.warning(
                            "Error sincronizando %s(%s): %s",
                            model._meta.label,
                            pk_val,
                            exc,
                        )

                resumen.append(
                    {
                        "modelo": model._meta.label,
                        "remotos": len(remotos),
                        "sincronizados": ok_count,
                        "errores": err_count,
                    }
                )
        finally:
            if is_sqlite:
                with local_conn.cursor() as cursor:
                    cursor.execute("PRAGMA foreign_keys = ON;")
    finally:
        _sync_state.running = False

    return resumen


def sincronizar_cambios_remota_a_local() -> dict:
    """
    Revisión incremental rápida (usada por El Celador automático):
    Compara conteo y PK máximo (y fecha de actualización si existe) entre Neon y SQLite.
    Solo descarga los registros nuevos o modificados sin bloquear la app.
    """
    if "remota" not in settings.DATABASES or "local" not in settings.DATABASES:
        return {"tablas_actualizadas": 0, "registros_descargados": 0}

    from config.utils import conexion_remota_disponible

    if not conexion_remota_disponible():
        return {"tablas_actualizadas": 0, "registros_descargados": 0}

    tablas_actualizadas = 0
    registros_descargados = 0
    local_conn = connections["local"]

    _sync_state.running = True
    try:
        is_sqlite = local_conn.vendor == "sqlite"
        if is_sqlite:
            with local_conn.cursor() as cursor:
                cursor.execute("PRAGMA foreign_keys = OFF;")

        try:
            for model in _resolver_modelos():
                pk_field = model._meta.pk.attname
                field_names = {f.name for f in model._meta.concrete_fields}
                ts_field = next(
                    (
                        cand
                        for cand in ("fecha_actualizacion", "updated_at", "fecha_modificacion", "last_login")
                        if cand in field_names
                    ),
                    None,
                )

                agg_kwargs = {"total": Count("pk"), "max_pk": Max("pk")}
                if ts_field:
                    agg_kwargs["max_ts"] = Max(ts_field)

                try:
                    rem_stats = model._base_manager.using("remota").aggregate(**agg_kwargs)
                    loc_stats = model._base_manager.using("local").aggregate(**agg_kwargs)
                except Exception as exc:
                    logger.debug("Celador omitió %s al comparar: %s", model._meta.label, exc)
                    continue

                rem_total = rem_stats.get("total") or 0
                loc_total = loc_stats.get("total") or 0
                if rem_total == 0:
                    continue

                # Modelos operativos clave sin timestamp explícito: refrescar los últimos 25 registros
                # para propagar cambios de estado (ej. pendiente -> autorizado -> en_ruta -> entregado).
                es_operativo_vivo = model._meta.label in {
                    "pedidos.Pedido",
                    "pedidos.DetallePedido",
                    "logistica.Entrega",
                    "logistica.Novedad",
                    "pagos.Pago",
                    "catalogo.Stock",
                    "usuarios.Notificacion",
                }

                hay_diferencia = (
                    rem_total != loc_total
                    or rem_stats.get("max_pk") != loc_stats.get("max_pk")
                    or (ts_field and rem_stats.get("max_ts") != loc_stats.get("max_ts"))
                    or es_operativo_vivo
                )
                if not hay_diferencia:
                    continue

                # Si solo hay filas nuevas con PK mayor y no cambió el timestamp de existentes,
                # descargamos únicamente las filas nuevas; si es operativo vivo sin cambios de conteo,
                # refrescamos solo los últimos 25 para mantener el ciclo ultra-rápido.
                loc_max_pk = loc_stats.get("max_pk")
                solo_nuevos = (
                    loc_max_pk is not None
                    and rem_total > loc_total
                    and (not ts_field or rem_stats.get("max_ts") == loc_stats.get("max_ts"))
                )
                qs = model._base_manager.using("remota").all()
                if solo_nuevos:
                    qs = qs.filter(**{f"{pk_field}__gt": loc_max_pk})
                elif es_operativo_vivo and rem_total == loc_total and rem_stats.get("max_pk") == loc_max_pk:
                    qs = qs.order_by(f"-{pk_field}")[:25]

                update_fields = [
                    f.attname for f in model._meta.concrete_fields if f.attname != pk_field
                ]
                copiados_tabla = 0
                for obj in qs:
                    valores = _concrete_field_values(obj)
                    try:
                        clon = model(**valores)
                        model._base_manager.using("local").bulk_create(
                            [clon],
                            update_conflicts=bool(update_fields),
                            unique_fields=[pk_field] if update_fields else None,
                            update_fields=update_fields or None,
                        )
                        copiados_tabla += 1
                    except Exception:
                        continue

                if copiados_tabla:
                    tablas_actualizadas += 1
                    registros_descargados += copiados_tabla
        finally:
            if is_sqlite:
                with local_conn.cursor() as cursor:
                    cursor.execute("PRAGMA foreign_keys = ON;")
    finally:
        _sync_state.running = False

    return {
        "tablas_actualizadas": tablas_actualizadas,
        "registros_descargados": registros_descargados,
    }


def _debe_iniciar_celador_automatico() -> bool:
    if os.getenv("DISABLE_CELADOR_AUTO", "").lower() in {"1", "true", "yes"}:
        return False
    if "remota" not in settings.DATABASES or "local" not in settings.DATABASES:
        return False
    if "test" in sys.argv or "pytest" in sys.modules:
        return False

    comandos_excluidos = {
        "migrate",
        "makemigrations",
        "collectstatic",
        "shell",
        "dbshell",
        "check",
        "dumpdata",
        "loaddata",
        "sincronizar",
        "sincronizar_local",
        "preparar_bd_offline",
        "changepassword",
        "createsuperuser",
    }
    if len(sys.argv) > 1 and sys.argv[1] in comandos_excluidos:
        return False

    # Con runserver y StatReloader, arrancar solo en el proceso hijo real (RUN_MAIN=true)
    if "runserver" in sys.argv and "--noreload" not in sys.argv:
        return os.environ.get("RUN_MAIN") == "true"

    # En WSGI (gunicorn) u otros servidores web, sí arrancar
    return "runserver" in sys.argv or "gunicorn" in (sys.argv[0] or "").lower()


def iniciar_celador_automatico() -> bool:
    """Inicia un hilo demonio liviano que revisa Neon periódicamente y descarga cambios a local."""
    global _celador_started
    if getattr(settings, "OFFLINE_MODE", False) or "remota" not in settings.DATABASES:
        return False
    if not _debe_iniciar_celador_automatico():
        return False

    with _celador_lock:
        if _celador_started:
            return False
        _celador_started = True

    intervalo = max(10, int(os.getenv("CELADOR_SYNC_INTERVAL_SECONDS", "15") or 15))

    def _loop_celador():
        # Esperar unos segundos al arranque para no competir con la primera carga del servidor
        time.sleep(5)
        while True:
            try:
                sub = sincronizar_pendientes_local_a_remota()
                if sub.get("registros_subidos", 0) > 0:
                    logger.info(
                        "[Celador] Subidos %s registros pendientes de local a Neon (%s tablas).",
                        sub["registros_subidos"],
                        sub["tablas_subidas"],
                    )
                res = sincronizar_cambios_remota_a_local()
                if res.get("registros_descargados", 0) > 0:
                    logger.info(
                        "[Celador] Descargados %s registros nuevos/actualizados de Neon a local (%s tablas).",
                        res["registros_descargados"],
                        res["tablas_actualizadas"],
                    )
            except Exception as exc:
                logger.debug("[Celador] Error en ciclo automático: %s", exc)
            finally:
                for alias in ("local", "remota"):
                    try:
                        if alias in connections:
                            connections[alias].close()
                    except Exception:
                        pass
            time.sleep(intervalo)

    t = threading.Thread(target=_loop_celador, name="CeladorNeonSync", daemon=True)
    t.start()
    logger.info("[Celador] Sincronizador automático bidireccional local <-> Neon iniciado (cada %ss).", intervalo)
    return True
