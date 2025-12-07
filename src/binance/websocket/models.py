from dataclasses import dataclass
import threading

@dataclass
class WebsocketCmd:
    id: str = ""
    cmd: str = "done" #ping, history, trade, user_data
    cmd_data : None = None
    respons_data : None = None  #Data that will be returned to not brake while loop
    diconnect : bool = False
    connected : bool = False


@dataclass
class CmdRequest:
    id: str
    cmd: str
    data: dict
    response_event: threading.Event
    response_value: object = None
    response_error: Exception | None = None
