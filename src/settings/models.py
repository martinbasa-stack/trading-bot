from dataclasses import dataclass, field
from typing import List

# Dynamic rule structure
# ================================
@dataclass
class IndicatorConfig:
    type_i: str = "SMA"
    sub_type: str = "none"
    interval: str = "1d"
    weight: int = 0
    block_trade_offset: float = 0.0
    value1: int = 20
    value2: int = 0
    value3: int = 0
    value4: int = 0
    output_select: str = "Upper"
    comparator: str = "Above"
    trigger: float = 50.0
    trigger_select: str = "Price"
    enable: bool = False
    factor: float = 0.0
    max_f: float = 0.0


# Asset Manager configuration
# ================================
@dataclass
class AssetManagerConfig:
    target: str = "Account"               # "Account" 
    symbol_index: int = 1       # which asset from the pair it manages
    max_spend_limit: float = 1000.0  # assetManageMaxSpendLimit
    min_save_limit: float = 50.0    # assetManageMinSaveLimit
    percent: int = 1            # assetManagePercent
    paper_t: bool = True

    # Buy/Sell parameters
    buy_base: float = 100.0
    buy_min: float = 50.0
    dip_buy: float = 2.0
    buy_max_factor: float = 50.0
    min_weight_buy: int = 0

    sell_base: float = 100.0
    sell_min: float = 50.0
    pump_sell: float = 2.0
    sell_max_factor: float = 50.0
    min_weight_sell: int = 0


# Main Strategy configuration
# ================================
@dataclass
class StrategyConfig:
    idx: int
    name: str = "NEW Strategy"
    type_s: str = "AdvancedDCA"
    symbol1: str = "BTC"
    flex_earn_s1: bool = False
    symbol2: str = "USDC"
    flex_earn_s2: bool = False
    run: bool = False
    candle_close_only: bool = False
    last_trade_as_min_max: bool = False
    candle_interval: str = "1d"
    lookback: int = 5
    time_limit_new_order: int = 300
    round_order: int = 2          # roundBuySellorder

    # Nested structures
    asset_manager: AssetManagerConfig = field(default_factory=AssetManagerConfig)
    indicators_buy: List[IndicatorConfig] = field(default_factory=list)
    indicators_sell: List[IndicatorConfig] = field(default_factory=list)

