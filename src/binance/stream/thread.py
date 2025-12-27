from .manager import StreamManager
from .stream import StreamWorker

from ..websocket.thread import ws_manager_obj

from src.settings.main import settings_obj, strategies_obj
from src.constants import LOG_PATH_BINANCE_API

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

binance_stream_man_obj = StreamManager(strategies_obj.get_pairs,
                                   lock=lock)

def stream_main():        
    """Create WebsocketConnection object and runs the object loop"""
    stream_conn_obj = StreamWorker(
        stream_manager=binance_stream_man_obj,
        get_pairs=strategies_obj.get_pairs,
        get_settings=settings_obj.get,
        lock=lock
        )
    stream_conn_obj.run() 





    