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
class Balance:
    available:  float
    locked: float
    total: float
