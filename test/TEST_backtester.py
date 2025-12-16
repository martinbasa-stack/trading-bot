from src.backtester.sequencer import Sequencer
from src.constants import FILE_PATH_HIST_STRATEGY
from src.settings import strategies_obj
from src.market_history import market_history_obj, fear_gread_obj
from src.strategy.dca import DCAstrategy
from src.strategy import TradeAnalyzer, IndicatorCompute, AssetAnalyzer, trade_manager_obj, Trade
from src.strategy.record_HL import HLRecordManager

import time

from datetime import datetime, timezone, timedelta

def _now():    
    now_utc = datetime.now(timezone.utc)
    return int(now_utc.timestamp()) 

start_time = _now()
shut_down = start_time + 120

#Create long lived objects
record_obj =  HLRecordManager(path=FILE_PATH_HIST_STRATEGY, get_list_of_id_pair=strategies_obj.get_id_pair_list)

sequencer_obj = Sequencer(
    get_by_id=strategies_obj.get_by_id,
    get_hist_table=market_history_obj.get_table,
    get_fng_timestamp=fear_gread_obj.get_timestamp,
    balance_s1= 1000,
    balance_s2=1000000
    )

# short lived objec declarations
trade_analyzer_obj = TradeAnalyzer(get_trade_table=trade_manager_obj.get_table,
                            get_hist_table=sequencer_obj.get_table,
                            get_by_id=strategies_obj.get_by_id
                            )

indicators_obj =IndicatorCompute(
    strategies_obj=strategies_obj,
    get_all_avg=trade_analyzer_obj.get_all_avgs,
    get_hist_table=sequencer_obj.get_table,
    get_close=sequencer_obj.get_close,
    fear_gread_get= sequencer_obj.get_fng_sim
    )
asset_analyzer_obj = AssetAnalyzer(
    get_by_id=strategies_obj.get_by_id,
    get_all_avg=trade_analyzer_obj.get_all_avgs,
    get_available_balance=sequencer_obj.get_available,
    get_close=sequencer_obj.get_close
)

dca_strategy = DCAstrategy(
        strategies_obj=strategies_obj,
        trade_analyzer_obj = trade_analyzer_obj,
        indicators_obj = indicators_obj,
        asset_analyzer_obj = asset_analyzer_obj,
        stream_get_close = sequencer_obj.get_close,
        record_obj = record_obj
    )

idx = sequencer_obj.strategy.idx
last_trade = None

trade_manager_obj.delete(idx, True)
interval = sequencer_obj.strategy.candle_interval

count = 0
stop = False
while not stop:
    stop = sequencer_obj.run()
    sequencer_obj._active_step

    #time.sleep(0.001)
    trade = dca_strategy.get_trade(idx)
    if trade:
        trade.timestamp = sequencer_obj.get_now_sim()
        #if not trade_manager_obj.get_table(idx):
        trade_manager_obj.new_trade(idx, trade, False)
        last_trade = trade

        sequencer_obj.update_balance(trade.quantity1, trade.quantity2)

        if trade:
            print(f"trade  {trade.quantity1}")
            print(f"trade  {trade.lookback}")

    #print(f"sequencer_obj._trackers {sequencer_obj._trackers} ")
        #print(f"Balance 1: = {round(sequencer_obj._balance_s1,6)}   Balance 2: = {round(sequencer_obj._balance_s2,2)} "  )
    #print(trade)
    #print(f"sequencer_obj.get_close {round(sequencer_obj.get_close("sdfg"),2)} ")   
    count +=1
    if count > 5000000:
        stop  = True

    if _now() > shut_down:
        stop  = True



#trade_manager_obj.new_trade(idx, last_trade, True)
print(f"Time to finish {timedelta(seconds = _now() - start_time)}")

#print(f"sequencer_obj.pnl {trade_analyzer_obj.get_pnl(idx,sequencer_obj.get_close(""))} ")   
print(f"Balance 1: = {round(sequencer_obj._balance_s1,6)}   Balance 2: = {round(sequencer_obj._balance_s2,2)} "  )
if trade_manager_obj.get_table(idx):
    print(f"trade_manager_obj.get_table {len(trade_manager_obj.get_table(idx))}")
print(f"count {count}")
print(f"sequencer_obj._save_candles {sequencer_obj._save_candles} ")    
print(f"sequencer_obj._save_candles {sequencer_obj._data_active.keys()} ")
print(f"sequencer_obj._trackers {sequencer_obj._trackers} ")
print(f"sequencer_obj._active_step {sequencer_obj._active_step} / {sequencer_obj._end_step}")
print("DONE -------------------------------------------------------")