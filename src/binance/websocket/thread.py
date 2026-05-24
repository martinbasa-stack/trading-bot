from src.settings.main import settings_obj, credentials_obj
from src.constants import FILE_PATH_EXCHANGE_INFO, LOG_PATH_BINANCE_API

from .manager import WebsocketManager
from .connection import WebsocketConnection

import logging
import threading

# Create a logger for this module
logger = logging.getLogger("binance")
logger.setLevel(logging.INFO)
# Prevent propagation to the root logger
logger.propagate = False
# Create a file handler for this module's log file
file_handler = logging.FileHandler(LOG_PATH_BINANCE_API)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(file_handler)

lock = threading.Lock()
event = threading.Event()

ws_manager_obj = WebsocketManager(
    path=FILE_PATH_EXCHANGE_INFO, 
    lock=lock, 
    event=event,
    settings_get=settings_obj.get                                                                              
    )

def websocet_main():
    """Create WebsocketConnection object and runs the object loop"""
    ws_conn_obj = WebsocketConnection(
        lock=lock, 
        event=event,
        ws_cmds= ws_manager_obj._ws_cmds,
        settings_get=settings_obj.get,
        credentials_get=credentials_obj.get
        )
    
    ws_conn_obj.run()