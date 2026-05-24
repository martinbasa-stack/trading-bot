import base64
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

import os
import json
import logging

# --- Logger Setup ---
logger = logging.getLogger("solana")

def derive_key(password: str, salt: bytes) -> bytes:
    kdf = Scrypt(
        salt=salt,
        length=32,
        n=2**14,
        r=8,
        p=1,
    )
    key = kdf.derive(password.encode("utf-8"))
    return base64.urlsafe_b64encode(key)


def load_json(path) ->dict:
    """
    Args:
        path(str):
            File path of .json.
    Returns:
        dict:
        Raw format form .json
    """
    try:
        if not os.path.exists(path):
            return None
        with open(path, "r") as jf: #open file
            return json.load(jf)  #return json
    except Exception as e:
        logger.error(f"load_json() error: {e}")

def save_json(path, data : dict): 
    """
    Args:
        path(str):
            File path of .json.
        data(dict):
            Raw data to be saved to .json.
    """
    try:   
        with open(path, "w") as jf: # save list of assets as JSON
            json.dump(data, jf, ensure_ascii=False, indent=4)   
    except Exception as e:
        logger.error(f"save_json() error: {e}")
