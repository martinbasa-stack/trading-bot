from dataclasses import dataclass

@dataclass
class Trade:
    timestamp:  int
    idx: str
    symbol1: str
    quantity1:  float
    symbol2: str
    quantity2:  float
    price: float
    change: float
    min_p : float
    max_p: float
    lookback: int
    avg_cost: float
    commision: float
    commision_symbol: str


@dataclass
class TradeTable:
    pair: str
    type_s : str
    symbol1: str
    symbol2: str
    paper: bool
    trades: list # -> list of TradeData 
    paper_trades: list # -> list of TradeData