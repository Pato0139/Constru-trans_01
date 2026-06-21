import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import requests
from django.conf import settings
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


def verify_license_token(token: str, secret: str) -> dict | None:
    """Verify a signed license token using HMAC-SHA256"""
    try:
        token_parts = token.split(".")
        if len(token_parts) != 2:
            return None
        payload_b64, signature = token_parts
        import base64

        payload_bytes = base64.b64decode(payload_b64.encode())
        payload = json.loads(payload_bytes)
        expected_signature = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_signature, signature):
            return None
        return payload
    except Exception:
        return None


def generate_license_token(customer_id: str, expires_days: int, secret: str) -> str:
    """Generate a signed license token"""
    import base64

    expires_at = timezone.now() + timedelta(days=expires_days)
    payload = {
        "customer_id": customer_id,
        "expires_at": expires_at.isoformat(),
        "created_at": timezone.now().isoformat(),
    }
    payload_bytes = base64.b64encode(json.dumps(payload).encode())
    signature = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return f"{payload_bytes.decode()}.{signature}"


def validate_license_remotely(inst: Installation) -> bool:
    """Validate license against remote server (optional, for production)"""
    remote_url = os.getenv("LICENSE_SERVER_URL")
    if not remote_url:
        return True
    try:
        response = requests.post(
            remote_url,
            json={
                "instance_id": str(inst.instance_id),
                "customer_id": inst.customer_id,
                "license_token": inst.license_token,
            },
            timeout=5,
        )
        if response.status_code == 200:
            return response.json().get("valid", False)
        return False
    except Exception:
        return True


def validate_installation():
    inst = create_or_get_installation()
    inst.last_validated_at = timezone.now()

    # Validate license token
    secret = os.getenv("LICENSE_SECRET", "default-secret-key-change-this-in-production")
    payload = None
    if inst.license_token:
        payload = verify_license_token(inst.license_token, secret)

    if not inst.license_token:
        inst.status = "pending"
    elif not payload:
        inst.status = "revoked"
    elif "expires_at" in payload:
        try:
            expires_at = datetime.fromisoformat(payload["expires_at"])
            expires_at = (
                timezone.make_aware(expires_at) if timezone.is_naive(expires_at) else expires_at
            )
            if timezone.now() > expires_at:
                inst.status = "expired"
        except Exception:
            inst.status = "tampered"
    elif (
        inst.build_hash != calculate_build_hash() or inst.manifest_hash != calculate_manifest_hash()
    ):
        inst.status = "tampered"
    elif not validate_license_remotely(inst):
        inst.status = "revoked"
    else:
        if payload:
            inst.customer_id = payload.get("customer_id", "")
        inst.status = "active"

    inst.save()
    return inst


def trigger_self_destruct():
    """Trigger self-destruct sequence: delete all database tables and files (use carefully!)"""
    import shutil

    from django.db import connection

    try:
        # Delete all data from the database (for SQLite)
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall() if row[0] != "sqlite_sequence"]
            for table in tables:
                cursor.execute(f"DROP TABLE IF EXISTS {table}")

        # Delete local database file
        db_path = settings.BASE_DIR / "db.sqlite3"
        if db_path.exists():
            os.remove(db_path)

        # Delete media files
        media_root = settings.MEDIA_ROOT
        if media_root.exists() and media_root.is_dir():
            shutil.rmtree(media_root)

    except Exception as e:
        print(f"Self-destruct failed: {e}")


def activate_license(customer_id: str, expires_days: int):
    """Activate a new license for this installation"""
    secret = os.getenv("LICENSE_SECRET", "default-secret-key-change-this-in-production")
    token = generate_license_token(customer_id, expires_days, secret)

    inst = create_or_get_installation()
    inst.customer_id = customer_id
    inst.license_token = token
    inst.activated_at = timezone.now()

    payload = verify_license_token(token, secret)
    if payload and "expires_at" in payload:
        inst.expires_at = datetime.fromisoformat(payload["expires_at"])
    inst.save()

    validate_installation()
    return inst
