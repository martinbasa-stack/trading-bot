import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from src.market_history import market_history_obj
from src.strategy.record_HL import HLRecord, HLRecordManager
from src.settings import settings_obj, strategies_obj
from src.strategy.trades import TradeAnalyzer, trade_manager_obj
from src.constants import FILE_PATH_HIST_STRATEGY
record_manager_obj = HLRecordManager(FILE_PATH_HIST_STRATEGY, strategies_obj.get_id_pair_list)
analyzer_obj = TradeAnalyzer(get_trade_table_func=trade_manager_obj.get_table,
                             get_hist_table_func=market_history_obj.get_table,
                             get_by_id_func=strategies_obj.get_by_id
                             )
strategy_id = strategies_obj.get_id_list()[-1]
strategy = strategies_obj.get_by_id(strategy_id)
pair = f"{strategy.symbol1}{strategy.symbol2}"
rec_id = f"{strategy_id}_{pair}"
print(f"TEST record_manager_obj {record_manager_obj.get(rec_id)}")
print(f"strategy_id = {strategy_id}")
print(f"TradeAnalyzer TEST get_avg_cost {analyzer_obj.get_avg_cost(strategy_id)}")
print(f"TradeAnalyzer TEST get_avg_entry {analyzer_obj.get_avg_entry(strategy_id)}")
print(f"TradeAnalyzer TEST get_avg_exit {analyzer_obj.get_avg_exit(strategy_id)}")
print(f"TradeAnalyzer TEST get_pnl {analyzer_obj.get_pnl(strategy_id, 3000)}")
print(f"TradeAnalyzer TEST get_avgs {analyzer_obj.get_avgs(strategy_id)}")
print(f"TradeAnalyzer TEST _interval {analyzer_obj._interval} _pair {analyzer_obj._pair} ")
print(f"TradeAnalyzer TEST get_kline_id_of_last_trade {analyzer_obj.get_kline_id_of_last_trade(strategy_id)}")
print(f"TradeAnalyzer TEST _interval {analyzer_obj._interval} _pair {analyzer_obj._pair} ")
print(f"TradeAnalyzer TEST get_min_max_price {analyzer_obj.get_min_max_price(strategy_id, record_manager_obj.get(rec_id))}")
print(f"TradeAnalyzer TEST _interval {analyzer_obj._interval} _pair {analyzer_obj._pair} ")
