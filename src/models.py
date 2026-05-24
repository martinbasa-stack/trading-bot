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
    available:  float = 0.0
    locked: float = 0.0
    total: float = 0.0
    savings: float = 0.0
    savings_wd: float = 0.0 # - Withdraw, + Deposit
    trade_reserve: float = 0.0
    min_trade_reserve: float = 0.0

