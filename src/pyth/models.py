from dataclasses import dataclass

@dataclass
class Feed:    
    idx : str
    base : str
    quote_currency : str
    symbol_code : str

@dataclass
class StreamData:
    time_ms : int
    feed_id: str
    close : float
    pair: str
    s1: str
    s2: str
    