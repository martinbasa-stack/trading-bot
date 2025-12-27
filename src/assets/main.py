from .manager import AssetManager

from src.binance.websocket.thread import ws_manager_obj
from src.solana_api.main import solana_man_obj

import asyncio
import threading

lock = threading.Lock()
asyc_update_queue = asyncio.Queue()

assets_man_binance_obj = AssetManager()
assets_man_solana_obj = AssetManager()

def update_assets_q(cmd: str = "all"):
    """
    Update assets.
    Args:
        cmd(str, Optional):
            
    """
    with lock:
        asyc_update_queue.put_nowait(cmd)

async def assets_main_task(shutdown : asyncio.Event):
    while not shutdown.is_set():
        cmd = await asyc_update_queue.get()
        await asyncio.sleep(0.5)
        match cmd:
            case "Binance":
                assets_man_binance_obj.update(ws_manager_obj.fetch_user_data())
            case "Solana":                
                if not solana_man_obj.locked:
                    assets_man_solana_obj.update(solana_man_obj.get_balances())
            case _:
                assets_man_binance_obj.update(ws_manager_obj.fetch_user_data())
                if not solana_man_obj.locked:
                    assets_man_solana_obj.update(solana_man_obj.get_balances())
        
        await asyncio.sleep(2)
        #print(f"solana_man_obj.get_balances {solana_man_obj.get_balances()}")
        #print(f"cmd {cmd}")
        #print(f"solana_man_obj.locked {solana_man_obj.locked}")
