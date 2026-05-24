import threading
import os
import webbrowser
import pystray
from pystray._base import Icon
from pystray import MenuItem as item, Menu as menu
from PIL import Image

from app import start_app, graceful_shutdown
from .utils import prompt_password
from .commands import ui_queue, ui_notify_msg, CMD_UNLOCK, CMD_EXIT,CMD_UI, CMD_NOTIFY

from src.constants import BASE_DIR
from src.settings.main import settings_obj
from src.assets.main import update_assets_q
from src.wallet.main import vault_obj, solana_wallet   # example

app_url = f"http://localhost:{settings_obj.get("Port")}/assets" 


def start_backend():
    threading.Thread(target=start_app, daemon=True).start()

def open_ui(icon: Icon, item: item):    
    ui_queue.put(CMD_UI)

def unlock_cmd(icon:Icon, item):
    ui_queue.put(CMD_UNLOCK)

def shutdown(icon: Icon, item):
    ui_queue.put(CMD_EXIT)


def unlock(icon:Icon, password):
    if vault_obj.unlock(password):
        icon.notify("Wallet unlocked")
        solana_wallet.load()
        update_assets_q("Solana")    
    else:        
        icon.notify("Wrong password!")
        

def open_logs(icon: Icon, item: item):
    path = BASE_DIR / "logs" / f"{item.text}.log"
    icon.notify((f"Opening log: \n"
                f"{path}"))    
    os.startfile(path)

def ui_loop(icon: Icon):
    while True:
        try:
            cmd = ui_queue.get(timeout=0.2)

            if cmd == CMD_UNLOCK:
                pw = prompt_password()
                if pw:
                    unlock(icon,pw)

            elif cmd == CMD_UI:                
                webbrowser.open_new_tab(app_url)
            
            elif cmd == CMD_NOTIFY:                
                msg = ui_notify_msg.get(timeout=0.2)             
                icon.notify(msg)
          
            elif cmd == CMD_EXIT:
                icon.notify("Shutting down!")
                graceful_shutdown()
                icon.stop()
                break  

        except Exception:
            pass

def create_tray():
    image = Image.open(BASE_DIR / "static" / "icon.ico")

    tray_menu : menu = (
        item("Open Web UI", open_ui),
        item("Unlock Wallet", unlock_cmd),
        menu.SEPARATOR,
        item("Logs",menu(
            item("app", open_logs),
            item("strategy", open_logs),
            item("settings_change", open_logs),
            item("solana", open_logs),
            item("pyth", open_logs),
            item("Binance_API", open_logs),
            item("main", open_logs),
        ) ),
        menu.SEPARATOR,
        item("Shutdown", shutdown),
    )

    icon = pystray.Icon(
        "TradingBot",
        image,
        "Trading Bot",
        tray_menu
    )
    
    icon.notify("Starting bot!")
    start_backend()
    threading.Thread(target=ui_loop, args=(icon,), daemon=True).start()
    icon.run()
