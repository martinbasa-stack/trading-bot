from dataclasses import dataclass

@dataclass
class StreamKline:
    time_ms : int
    open_ : float
    close : float
    high: float
    low: float
    volume: float
    interval : str
