import base64
from .create import unlock_wallet

class SecretVault:
    def __init__(self, encrypted_blob: dict):
        self._encrypted_blob = encrypted_blob
        self._salt = base64.b64decode(encrypted_blob["salt"])
        self._secret: bytes | None = None

    @property
    def locked(self):
        if self._secret:
            return False
        return True

    def reload(self, encrypted_blob: dict):
        self._encrypted_blob = encrypted_blob

    def unlock(self, password: str):
        self._secret = unlock_wallet(self._encrypted_blob, password)
        if not self._secret:
            return False
        return True

    def get_seed(self) -> str:
        if self._secret is None:
            raise RuntimeError("Vault locked")
        return self._secret

    def lock(self):
        self._secret = None
