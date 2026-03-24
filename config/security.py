import os
import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional


class SecurityManager:
    SALT_FILE = ".smb_salt"
    ITERATIONS = 100000
    DEFAULT_MASTER_PASSWORD = "admin"

    def __init__(self):
        self._key: Optional[bytes] = None
        self._salt = self._load_or_create_salt()
        self._is_default_password = False

    def _load_or_create_salt(self) -> bytes:
        if os.path.exists(self.SALT_FILE):
            try:
                with open(self.SALT_FILE, "rb") as f:
                    return f.read()
            except:
                pass
        salt = os.urandom(16)
        try:
            with open(self.SALT_FILE, "wb") as f:
                f.write(salt)
        except:
            pass
        return salt

    def _derive_key(self, master_password: str) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._salt,
            iterations=self.ITERATIONS,
        )
        return base64.urlsafe_b64encode(kdf.derive(master_password.encode()))

    def set_master_password(self, master_password: str):
        self._key = self._derive_key(master_password)
        self._is_default_password = (master_password == self.DEFAULT_MASTER_PASSWORD)

    def is_unlocked(self) -> bool:
        return self._key is not None

    def is_using_default_password(self) -> bool:
        return self._is_default_password

    def lock(self):
        self._key = None
        self._is_default_password = False

    def encrypt(self, plaintext: str) -> str:
        if not self._key:
            raise ValueError("未解锁，请先输入主密码")
        f = Fernet(self._key)
        return f.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        if not self._key:
            raise ValueError("未解锁，请先输入主密码")
        f = Fernet(self._key)
        return f.decrypt(ciphertext.encode()).decode()

    def verify_master_password(self, master_password: str) -> bool:
        try:
            test_key = self._derive_key(master_password)
            f = Fernet(test_key)
            f.encrypt(b"test")
            return True
        except:
            return False

    def reset_to_default(self):
        if os.path.exists(self.SALT_FILE):
            try:
                os.remove(self.SALT_FILE)
            except:
                pass
        self._salt = os.urandom(16)
        try:
            with open(self.SALT_FILE, "wb") as f:
                f.write(self._salt)
        except:
            pass
        self._key = None
        self._is_default_password = False
