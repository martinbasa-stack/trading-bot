from .manager import HistoryManager
from .models import PairHistory, IntervalData
from src.settings import strategies_class

history_class = HistoryManager(get_pairs_intervals_func=strategies_class.generate_pairs_intervals)
