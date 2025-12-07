from .manager import MarketHistoryManager
from .models import PairHistory, IntervalData
from src.settings import strategies_obj, settings_obj

market_history_obj = MarketHistoryManager(get_pairs_intervals=strategies_obj.generate_pairs_intervals,
                                          settings_get=settings_obj.get                                          
                                          )
