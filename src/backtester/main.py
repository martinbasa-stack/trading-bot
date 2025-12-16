from .sequencer import Sequencer

from src.settings import strategies_obj
from src.market_history import market_history_obj, fear_gread_obj
from src.strategy.dca import DCAstrategy
from src.strategy import TradeAnalyzer, IndicatorCompute, AssetAnalyzer, trade_manager_obj, Trade
from src.strategy.run import record_obj

import time
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger("app").getChild(__name__)

def run_backtester(balance_s1, balance_s2):
    try:
        
        start_time = _now()     
        shut_down = start_time + 300 #Max run time in s

        sequencer_obj = Sequencer(
        get_by_id=strategies_obj.get_by_id,
        get_hist_table=market_history_obj.get_table,
        get_fng_timestamp=fear_gread_obj.get_timestamp,
        balance_s1= balance_s1,
        balance_s2=balance_s2
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
        s1 = sequencer_obj.strategy.symbol1
        s2 = sequencer_obj.strategy.symbol2

        trade_manager_obj.delete(idx, True)

        # Runn backtester loop
        stop = False
        while not stop:
            stop = sequencer_obj.run()
            sequencer_obj._active_step

            trade = dca_strategy.get_trade(idx)
            if trade:
                trade.timestamp = sequencer_obj.get_now_sim()
                trade.idx = "backtester"
                trade_manager_obj.new_trade(idx, trade, False)
                
                sequencer_obj.update_balance(trade.quantity1, trade.quantity2)
   

            if shut_down < _now(): # Safety shut down
                stop  = True

        return (f"Run time {timedelta(seconds = _now() - start_time)}"
                f"\n Final balance: {sequencer_obj.get_available(s1)} {s1} | {sequencer_obj.get_available(s2)} {s2}"
                )
    
    except Exception as e:
        logger.error(f"run_backtester() error : {e}")



def _now():    
    now_utc = datetime.now(timezone.utc)
    return int(now_utc.timestamp()) 