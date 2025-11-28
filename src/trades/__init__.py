from .models import Trade, TradeTable
from .manager import TradeManager
from src.settings import strategies_class

trade_manager_class = TradeManager(get_strategies_ids_func=strategies_class.id_list, get_strategy_by_id_func=strategies_class.get_by_id)