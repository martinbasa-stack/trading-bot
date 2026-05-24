from src.utils.storage import save_json, load_json

import threading
import logging

from pathlib import Path
from typing import Any, Dict
import os
from dotenv import load_dotenv, set_key
from cryptography.fernet import Fernet
import bcrypt

ENV_PATH=".venv/.env"
# CredentialsManager Class (long-living)
# ----------------------------------------------------------------------
class CredentialsManager:
    """ (long-living) Class for storing and managin credentials
            saving and loading from .json file
            Main class that others depend on!
    """
    #Manage loading, updating and saving settings stored in a JSON file.

    def __init__(self, file_path: str):  
        """
        Args:
            file_path(str): path to the .json file of all hashed credentials
        """        
        self._cred_path = Path(file_path)
        #threading
        self._lock = threading.Lock()

        # --- Logger Setup ---
        self._logger = logging.getLogger("settings").getChild(self.__class__.__name__)

        # Load settings immediately
        self._data: Dict[str, Any] = {}        
        self._data = self._load()
        
        # load key
        self._enc_key = None    
        self._create_env_file_if_not_exists()
        self._load_env()

    # Internal JSON I/O
    # ==================================================================
    def _load(self) -> Dict[str, Any]:
        #Load settings from the JSON file.
        try:
            if not self._cred_path.exists():
                self._logger.warning(f"Config file not found, creating default empty file.")
                self._cred_path.write_text("{}")
            loda_data = load_json(self._cred_path)
            return loda_data
        except Exception as e:
            self._logger.error(f"Error loading credentials: {e}")
            return loda_data

    def _save(self) -> None:
        #Write settings back to JSON
        try:
            save_json(self._cred_path, self._data)            
        except Exception as e:
            self._logger.error(f"Error saving credentials: {e}")

    # Key and .env load and creation
    # ==================================================================
    def _create_env_file_if_not_exists(self):
        """
        Creates a .env file if it does not already exist, 
        and adds default content.
        """
        # Use pathlib for path manipulation
        env_path = Path(ENV_PATH)

        if not env_path.is_file():
            try:
                key = Fernet.generate_key()                
                self._enc_key = key
                key_dec = key.decode("utf-8")
                with open(env_path, 'x') as f:
                    # Open the file in 'x' (exclusive creation) mode, which creates 
                    f.write("# Environment variables for the project\n")
                    f.write(f"ENC_KEY={key_dec}\n")
                self._logger.info(f"'{ENV_PATH}' created successfully with default content.")
            except FileExistsError:
                self._logger.error(f"'{ENV_PATH}' already exists.")
            except IOError as e:
                self._logger.error(f"Error creating file: {e}")    
    
    # Load env vars
    # ------------------------------------------------------------
    def _load_env(self):
        load_dotenv(ENV_PATH)
        k = "ENC_KEY"
        key = os.getenv(k)
        if not key:
            key = Fernet.generate_key()
            key_dec = key.decode("utf-8")
            set_key(ENV_PATH, k, key_dec)
        else:
            key = key.encode("utf-8")

        self._enc_key = key

    # Public 
    # ==================================================================
    # Read one value
    # -----------------------------------------------------------
    def get(self, key: str, default: Any = None) -> Any:
        try:
            with self._lock:
                f = Fernet(self._enc_key)
                encrypted = self._data.get(key, default)
                if not encrypted:
                    return default
                decryptede = f.decrypt(str(encrypted).encode("utf-8"))            
                return decryptede.decode("utf-8")# Decode bytes back 
        except Exception as e:
            self._logger.error(f"Get decrypted error: {e}")

    # Save encrypted
    # -----------------------------------------------------------
    def set(self, password,  key: str, value) -> None:
        try:
            if not self.validate("password", password):
                return
            with self._lock:
                value_bytes = str(value).encode("utf-8")
                f = Fernet(self._enc_key)
                encrypted = f.encrypt(value_bytes)
                self._data[key] = encrypted.decode("utf-8")
                self._save()
            
        except Exception as e:
            self._logger.error(f"Set decrypted error: {e}")
    
    # Save hashed
    # -----------------------------------------------------------
    def set_hashed(self, password,  key: str, value: Any) -> None:
        try:
            if not self.validate("password", password) and key !="password":
                return
            if len(value)< 1:
                return
            
            with self._lock:
                value_bytes = str(value).encode("utf-8")
                hashed = bcrypt.hashpw(value_bytes, bcrypt.gensalt())
                self._data[key] = hashed.decode("utf-8")
                self._save()

            return True
                
        except Exception as e:
            self._logger.error(f"Set hashed error: {e}")

    # validate hashed
    # -----------------------------------------------------------
    def validate(self, key,  value) -> bool:
        try:
            with self._lock:
                value_bytes = str(value).encode("utf-8")
                hashed = self._data.get(key)
                if not hashed:
                    return False
                return bcrypt.checkpw(value_bytes, str(hashed).encode("utf-8"))

        except Exception as e:
            self._logger.error(f"Validate error: {e}")
            return False


        
    

    