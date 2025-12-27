from .manager import TradeManager

from src.settings.main import strategies_obj, settings_obj

trade_manager_obj = TradeManager(
    strategies_obj=strategies_obj, 
    get_settings=settings_obj.get
    )