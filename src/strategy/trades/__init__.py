from .models import Trade, TradeTable, AverageSum, PnL
from .manager import TradeManager
from .analyzer import TradeAnalyzer
from src.settings import strategies_obj, settings_obj

trade_manager_obj = TradeManager(
    strategies_obj=strategies_obj, 
    get_settings=settings_obj.get
    )