from .manager import AssetManager

from src.binance.websocket.thread import ws_manager_obj
from src.solana_api.main import solana_man_obj
from src.settings.main import strategies_obj
from src.pyth.main import pyth_data_obj
from src.binance.stream.thread import binance_stream_man_obj

import asyncio
import threading
from datetime import datetime, timezone

lock = threading.Lock()
asyc_update_queue = asyncio.Queue()

assets_man_binance_obj = AssetManager(
    strategies_obj=strategies_obj,
    strat_type="Binance_CEX",
    get_price=binance_stream_man_obj.get_close
)
assets_man_solana_obj = AssetManager(    
    strategies_obj=strategies_obj,
    strat_type="Solana_Raydium_DEX",
    get_price=pyth_data_obj.get_close
)


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
        
        print(f"DEBUG cmd: {cmd}")
        match cmd:
            case "Binance":
                await _update_binance()
            case "Solana":                
                await _update_solana()
            case _:
                await _update_binance()
                await _update_solana()
        
        await asyncio.sleep(10)

async def _update_solana():    
    if solana_man_obj.locked:
        return
    
    solana_man_obj.run_clenup()
    i = 10
    balaces = None
    while not balaces and i>0:
        i -=1
        balaces = solana_man_obj.get_balances()
        print(f"DEBUG --------------------------------------")
        print(f"DEBUG {balaces}")
        if not balaces:
            await asyncio.sleep(1)
    assets_man_solana_obj.update(balaces)
    update = solana_man_obj.savings_update(assets_man_solana_obj.get_all())
    if update:
        await asyncio.sleep(2)
        i = 10 # Max retries
        while solana_man_obj.pending_savings_trx() and i>0:
            print(f"DEBUG update try: {i}")
            i -=1
            await asyncio.sleep(2)
            solana_man_obj.run_clenup()
            
        assets_man_solana_obj.update(solana_man_obj.get_balances())        

    print(f"DEBUG ------END --------------------------------")
async def _update_binance():    
    assets_man_binance_obj.update(ws_manager_obj.fetch_user_data())

def _now():        
    now_utc = datetime.now(timezone.utc)
    return int(now_utc.timestamp()) 