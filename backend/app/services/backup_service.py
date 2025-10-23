"""Backup and restore service"""
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os


def derive_key(password: str, salt: bytes) -> bytes:
    """Derive encryption key from password"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key


def encrypt_backup(data: bytes, password: str) -> bytes:
    """Encrypt backup data with password"""
    salt = os.urandom(16)
    key = derive_key(password, salt)
    f = Fernet(key)
    encrypted_data = f.encrypt(data)
    # Prepend salt to encrypted data
    return salt + encrypted_data


def decrypt_backup(encrypted_data: bytes, password: str) -> bytes:
    """Decrypt backup data with password"""
    # Extract salt from beginning
    salt = encrypted_data[:16]
    encrypted = encrypted_data[16:]
    
    key = derive_key(password, salt)
    f = Fernet(key)
    return f.decrypt(encrypted)
