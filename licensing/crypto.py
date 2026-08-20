# licensing/crypto.py
import os
from argon2.low_level import hash_secret_raw, Type
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

AAD = b"constru-trans-lic-v1"

# Parametros Argon2id — OWASP 2026 baseline
KDF_DEFAULTS = {"time_cost": 3, "memory_cost": 65536, "parallelism": 2, "hash_len": 32}


def derive_key(password: str, salt: bytes, params: dict | None = None) -> bytes:
    p = {**KDF_DEFAULTS, **(params or {})}
    return hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=salt,
        time_cost=p["time_cost"],
        memory_cost=p["memory_cost"],
        parallelism=p["parallelism"],
        hash_len=p["hash_len"],
        type=Type.ID,
    )


def encrypt_license_blob(plaintext: bytes, password: str) -> dict:
    salt = os.urandom(16)
    key = derive_key(password, salt)
    nonce = os.urandom(12)
    ct = AESGCM(key).encrypt(nonce, plaintext, AAD)
    return {"salt": salt, "nonce": nonce, "ciphertext": ct}


def decrypt_license_blob(blob: dict, password: str) -> bytes:
    key = derive_key(password, blob["salt"])
    # cryptography.exceptions.InvalidTag si el archivo fue manipulado o el password es incorrecto.
    return AESGCM(key).decrypt(blob["nonce"], blob["ciphertext"], AAD)
