import hashlib
import os
from pathlib import Path
from django.utils import timezone
from .models import Installation
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
import json, logging

from .crypto import encrypt_license_blob, decrypt_license_blob, KDF_DEFAULTS
from .models import Licencia, UsuarioLicencia, AuditoriaLicencia

User = get_user_model()
logger = logging.getLogger(__name__)


def get_current_installation() -> Installation | None:
    try:
        return Installation.objects.first()
    except Installation.DoesNotExist:
        return None


def calculate_build_hash() -> str:
    base_dir = Path(__file__).resolve().parent.parent.parent
    hash_sha256 = hashlib.sha256()

    try:
        for file in ["requirements.txt", "pyproject.toml", "manage.py", "core/settings/base.py"]:
            file_path = base_dir / file
            if file_path.exists():
                with open(file_path, "rb") as f:
                    hash_sha256.update(f.read())
    except Exception:
        pass
    return hash_sha256.hexdigest()


def calculate_manifest_hash() -> str:
    base_dir = Path(__file__).resolve().parent.parent.parent
    hash_sha256 = hashlib.sha256()

    try:
        apps_dir = base_dir / "apps"
        for root, _, files in os.walk(apps_dir):
            for file in files:
                if file.endswith(".py"):
                    file_path = Path(root) / file
                    with open(file_path, "rb") as f:
                        hash_sha256.update(f.read())
    except Exception:
        pass
    return hash_sha256.hexdigest()


def create_or_get_installation() -> Installation:
    inst = get_current_installation()
    if not inst:
        inst = Installation.objects.create(
            build_hash=calculate_build_hash(), manifest_hash=calculate_manifest_hash()
        )
    return inst


def validate_installation():
    inst = create_or_get_installation()
    inst.last_validated_at = timezone.now()

    if not inst.expires_at:
        inst.status = "pending"
    elif timezone.now() > inst.expires_at:
        inst.status = "expired"
    elif (
        inst.build_hash != calculate_build_hash() or inst.manifest_hash != calculate_manifest_hash()
    ):
        inst.status = "tampered"
    else:
        inst.status = "active"

    inst.save()
    return inst

def crear_licencia(*, codigo, nombre, password, permisos_codenames,
                   duracion_dias=365, descripcion="") -> Licencia:
    """Crea Licencia; cifra metadatos con la contraseña provista."""
    payload = json.dumps({
        "codigo": codigo, "nombre": nombre,
        "permisos": list(permisos_codenames),
        "emitido_en": timezone.now().isoformat(),
    }, ensure_ascii=False).encode("utf-8")

    blob = encrypt_license_blob(payload, password)
    perms = list(Permission.objects.filter(codename__in=permisos_codenames))

    with transaction.atomic():
        lic = Licencia.objects.create(
            codigo=codigo, nombre=nombre, descripcion=descripcion,
            permisos=perms,
            fecha_emision=timezone.now(),
            fecha_expiracion=timezone.now() + timedelta(days=duracion_dias),
            archivo_cifrado_nonce=blob["nonce"],
            archivo_cifrado_ciphertext=blob["ciphertext"],
            password_salt=blob["salt"],
            password_kdf_params=KDF_DEFAULTS,
        )
        return lic


def asignar_licencia(usuario, licencia, *, asignada_por=None, ip=None) -> UsuarioLicencia:
    with transaction.atomic():
        ul, creada = UsuarioLicencia.objects.get_or_create(
            usuario=usuario, licencia=licencia,
            fecha_desasignacion__isnull=True,
            defaults={"asignada_por": asignada_por, "ip_asignacion": ip},
        )
    if not creada:
        # Reasignación tras desasignación previa
        ul.fecha_desasignacion = None
        ul.save(update_fields=["fecha_desasignacion"])
    AuditoriaLicencia.objects.create(
        licencia=licencia, usuario_afectado=usuario, actor=asignada_por,
        accion="LICENCIA_ASIGNADA", ip=ip, exitosa=True,
        detalle=f"{licencia.codigo} → {usuario.username}",
    )
    return ul


def revocar_licencia(licencia, *, actor, motivo="", ip=None) -> Licencia:
    with transaction.atomic():
        licencia.estado = "revocada"
        licencia.revocada_en = timezone.now()
        licencia.revocada_por = actor
        licencia.motivo_revocacion = motivo
        licencia.save(update_fields=["estado", "revocada_en", "revocada_por", "motivo_revocacion"])
        UsuarioLicencia.objects.filter(licencia=licencia,
                                         fecha_desasignacion__isnull=True).update(
            fecha_desasignacion=timezone.now(),
            motivo_desasignacion=f"Revocada: {motivo}",
        )
    AuditoriaLicencia.objects.create(
        licencia=licencia, actor=actor, accion="LICENCIA_REVOCADA",
        ip=ip, detalle=motivo,
    )
    return licencia


def rotar_password(licencia, new_password) -> Licencia:
    payload = json.dumps({
        "codigo": licencia.codigo, "nombre": licencia.nombre,
        "permisos": list(licencia.permisos.values_list("codename", flat=True)),
    }, ensure_ascii=False).encode("utf-8")
    blob = encrypt_license_blob(payload, new_password)
    licencia.archivo_cifrado_nonce = blob["nonce"]
    licencia.archivo_cifrado_ciphertext = blob["ciphertext"]
    licencia.password_salt = blob["salt"]
    licencia.rotaciones_password += 1
    licencia.ultima_rotacion_password = timezone.now()
    licencia.save(update_fields=[
        "archivo_cifrado_nonce", "archivo_cifrado_ciphertext",
        "password_salt", "rotaciones_password", "ultima_rotacion_password",
    ])
    return licencia


def tiene_licencia_vigente(usuario) -> bool:
    asignaciones = UsuarioLicencia.objects.filter(
        usuario=usuario, fecha_desasignacion__isnull=True,
    ).select_related("licencia")
    return any(a.licencia.esta_vigente for a in asignaciones)


def permisos_de_usuario(usuario) -> set[str]:
    """Devuelve la unión de permisos de todas las licencias vigentes del usuario."""
    codenames = set()
    for ul in UsuarioLicencia.objects.filter(
        usuario=usuario, fecha_desasignacion__isnull=True,
    ).select_related("licencia"):
        if ul.licencia.esta_vigente:
            codenames.update(
                ul.licencia.permisos.values_list("content_type__app_label",
                                                 "codename")
            )
    return {f"{app}.{code}" for app, code in codenames}