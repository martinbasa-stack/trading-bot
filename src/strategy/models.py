from dataclasses import dataclass

@dataclass
class TriggerComputeResult:
    strategy_idx: int
    trade_enable : bool = False

    buy_sum_trigger : bool = False
    buy_ind_trade_en : bool = False
    dca_buy_trigger : bool = False
    buy_weight: int = 0.0
    buy_factor : float = 0.0
    to_buy : float = 0.0
    percent_change_dip: float = 0.0
    min_price : float = 0.0

    sell_sum_trigger : bool = False
    sell_ind_trade_en : bool = False
    dca_sell_trigger : bool = False
    sell_weight : int = 0.0
    sell_factor : float = 0.0
    to_sell : float = 0.0
    percent_change_pump: float = 0.0
    max_price : float = 0.0
