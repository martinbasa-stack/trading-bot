import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from src.market_history import market_history_obj,IntervalData
from src.strategy.record_HL import HLRecord, HLRecordManager
from src.settings import settings_obj, strategies_obj
from src.strategy.trades import TradeAnalyzer, trade_manager_obj
from src.strategy.indicators.compute import IndicatorCompute
from src.constants import FILE_PATH_HIST_STRATEGY,FILE_PATH_FEAR_GREAD
from src.strategy.fear_gread.fear_gread import FearAndGread

fear_gread_obj = FearAndGread(path=FILE_PATH_FEAR_GREAD)
fear_gread = fear_gread_obj.get()
record_manager_obj = HLRecordManager(FILE_PATH_HIST_STRATEGY, strategies_obj.get_id_pair_list)
analyzer_obj = TradeAnalyzer(get_trade_table=trade_manager_obj.get_table,
                             get_hist_table=market_history_obj.get_table,
                             get_by_id=strategies_obj.get_by_id
                             )
def test_last_close(pair, max_old: int = 0):
    table: IntervalData = market_history_obj.get_table(pair, "4h")
    price = table.close[-1]
    return price
indicators_obj =IndicatorCompute(
    get_all_avg=analyzer_obj.get_all_avgs,
    strategies_obj=strategies_obj,
    get_hist_table=market_history_obj.get_table,
    get_close=test_last_close,
    fear_gread=fear_gread.value
    )

strategy_id = strategies_obj.get_id_list()[-1]
strategy = strategies_obj.get_by_id(strategy_id)
pair = f"{strategy.symbol1}{strategy.symbol2}"
rec_id = f"{strategy_id}_{pair}"
print(f"TEST record_manager_obj {record_manager_obj.get(rec_id)}")
print(f"strategy_id = {strategy_id}")
results = indicators_obj.get_buy_list(strategy_id)
for result in results:
    print(f"indicators_obj.get_buy_list = {result}")
    print(f"------------------------------------------------------------")

results = indicators_obj.get_sell_list(strategy_id)
for result in results:
    print(f"indicators_obj.get_sell_list = {result}")
    print(f"------------------------------------------------------------")
print(f"indicators_obj.get_buy_compute = {indicators_obj.get_buy_compute(strategy_id)}")
print(f"indicators_obj.get_sell_compute = {indicators_obj.get_sell_compute(strategy_id)}")

