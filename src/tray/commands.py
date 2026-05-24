import queue
import threading

ui_queue = queue.Queue()
ui_notify_msg = queue.Queue()
th_lock = threading.Lock()

CMD_UNLOCK = "unlock"
CMD_EXIT   = "exit"
CMD_UI     = "open_ui"
CMD_NOTIFY     = "notify"

def notify_put(msg: str):
    with th_lock:
        ui_notify_msg.put_nowait(msg)
        ui_queue.put_nowait(CMD_NOTIFY)