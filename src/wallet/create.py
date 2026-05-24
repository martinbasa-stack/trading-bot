import os
import base64
import bcrypt
from cryptography.fernet import Fernet

from .utils import derive_key, save_json
from ..constants import FILE_PATH_WALLET

from mnemonic import Mnemonic

def generate_seed_phrase(language:str = "english") -> str:
    mnemo = Mnemonic(language)
    return mnemo.generate(strength=256)  # 24 words

def mnemo_languages() -> list[str]:
    return Mnemonic.list_languages()

def create_wallet(password: str, mnemonic_phrase: str, language : str =  "english") -> str:
        salt = os.urandom(16)
        if len(password)< 5:
            return "Password is to short! Minumum 6 chars."
        mnemo = Mnemonic(language)
        if not mnemo.check(mnemonic_phrase):
              return f"'{mnemonic_phrase}' is not mnemonic phrase!"
        
        seed = Mnemonic.to_seed(mnemonic_phrase)

        # derive encryption key
        fernet_key = derive_key(password, salt)
        f = Fernet(fernet_key)

        encrypted_seed = f.encrypt(seed)

        password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        )

        save_json(FILE_PATH_WALLET ,{
            "salt": base64.b64encode(salt).decode(),
            "password_hash": base64.b64encode(password_hash).decode(),
            "encrypted_seed":  base64.b64encode(encrypted_seed).decode(),
        }) 
        return "Wallet created and encoded."

def unlock_wallet(encrypted_blob: dict, password: str) -> str:
        salt = base64.b64decode(encrypted_blob["salt"])
        password_hash = base64.b64decode(encrypted_blob["password_hash"])
        encrypted_seed = base64.b64decode(encrypted_blob["encrypted_seed"])

        # verify password first
        if not bcrypt.checkpw(password.encode("utf-8"), password_hash):
            raise ValueError("Invalid password")

        # derive same key
        fernet_key = derive_key(password, salt)
        f = Fernet(fernet_key)

        return f.decrypt(encrypted_seed)

