from dataclasses import dataclass

@dataclass
class Balance:
    available:  float
    locked: float
    total: float


@dataclass
class Assets:
    symbol: str
    balance: Balance 

@dataclass
class AssetManagerResult:
    to_buy: float = 0.0
    available_s1: float = 0.0
    s2_balance_ok :bool = False
    to_sell : float = 0.0
    available_s2 : float = 0.0
    s1_balance_ok:bool = False




