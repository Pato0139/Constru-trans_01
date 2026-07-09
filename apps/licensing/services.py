import hashlib
import os
from pathlib import Path

from django.utils import timezone

from .models import Installation


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
