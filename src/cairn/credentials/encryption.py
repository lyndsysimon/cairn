"""Fernet-based symmetric encryption for credential values at rest.

Derives a stable Fernet key from a user-supplied passphrase using PBKDF2.
"""

import base64

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Fixed application salt for deterministic key derivation.
# The passphrase (CAIRN_ENCRYPTION_KEY) provides the actual entropy.
_SALT = b"cairn-credential-store-v1"
_ITERATIONS = 480_000


def derive_key(passphrase: str) -> bytes:
    """Derive a Fernet key from a passphrase via PBKDF2."""
    if not passphrase:
        raise ValueError("Encryption key must not be empty")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_SALT,
        iterations=_ITERATIONS,
    )
    raw = kdf.derive(passphrase.encode("utf-8"))
    return base64.urlsafe_b64encode(raw)


def encrypt_value(plaintext: str, key: bytes) -> bytes:
    """Encrypt a credential value. Returns Fernet ciphertext bytes."""
    f = Fernet(key)
    return f.encrypt(plaintext.encode("utf-8"))


def decrypt_value(ciphertext: bytes, key: bytes) -> str:
    """Decrypt a credential value. Raises InvalidToken on failure."""
    f = Fernet(key)
    return f.decrypt(ciphertext).decode("utf-8")
