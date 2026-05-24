from dataclasses import dataclass

@dataclass
class IndicatorResult:
    enable_trade: bool = False
    weight: int = 0

    out_val: float = 0.0
    trigger: float = 0.0
    trigger_offset: float = 0.0
    delta: float = 0.0

    factor: float = 0.0
    factor_limit: float = 0.0

    dis_text: str = ""