from dataclasses import dataclass

@dataclass
class TradeTable:
    pair: str
    type_s : str
    symbol1: str
    symbol2: str
    paper: bool
    trades: list # -> list of TradeData 
    paper_trades: list # -> list of TradeData

@dataclass
class AverageSum:
    avg: float = 0.0
    sum1: float = 0.0
    sum2: float = 0.0
    num: int = 0

@dataclass
class PnL:
    realised: float = 0.0
    real_percent: float = 0.0
    unrealised: float = 0.0
    unreal_percent: float = 0.0
    total: float = 0.0
    total_percent: float = 0.0