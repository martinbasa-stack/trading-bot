from..constants import(
    LOG_PATH_STRATEGY,
    FILE_PATH_HIST_STRATEGY
)
from src.binance import stream_manager_obj, ws_manager_obj 
from src.settings import settings_obj, strategies_obj
from ..market_history import market_history_obj, fear_gread_obj
from .trades import trade_manager_obj, Trade, TradeAnalyzer
from .assets import AssetAnalyzer, asset_manager_obj
from .indicators import IndicatorCompute
from .record_HL.manager import HLRecordManager
from src.telegram import send_telegram_msg

from .dca import DCAstrategy

import logging
from datetime import datetime, timezone
import time


#get current time data
now_utc = datetime.now(timezone.utc)
timestamp_seconds = int(now_utc.timestamp())

# Create a logger for this module
logger = logging.getLogger("strategy")
logger.setLevel(logging.INFO)
# Prevent propagation to the root logger
logger.propagate = False
# Create a file handler for this module's log file
file_handler = logging.FileHandler(LOG_PATH_STRATEGY, mode="a")
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


#Globals
#Create long lived objects
record_obj =  HLRecordManager(path=FILE_PATH_HIST_STRATEGY, get_list_of_id_pair=strategies_obj.get_id_pair_list)


#Call the strategies -------------------------------------------------------------------------------------------
def strategy_run():
    """Main strategy run logic and trade execution."""
    try:        
        # short lived objec declarations
        trade_analyzer_obj = TradeAnalyzer(get_trade_table=trade_manager_obj.get_table,
                                    get_hist_table=market_history_obj.get_table,
                                    get_by_id=strategies_obj.get_by_id
                                    )
        indicators_obj =IndicatorCompute(
            strategies_obj=strategies_obj,
            get_all_avg=trade_analyzer_obj.get_all_avgs,
            get_hist_table=market_history_obj.get_table,
            get_close=stream_manager_obj.get_close,
            fear_gread_get= fear_gread_obj.get
            )
        asset_analyzer_obj = AssetAnalyzer(
            get_by_id=strategies_obj.get_by_id,
            get_all_avg=trade_analyzer_obj.get_all_avgs,
            get_available_balance=asset_manager_obj.get_available,
            get_close=stream_manager_obj.get_close
        )
        #Call cleenup and run checks
        record_obj.cleanup()
        trade_manager_obj.cleanup()

        dac_strategy = DCAstrategy(
                strategies_obj=strategies_obj,
                trade_analyzer_obj = trade_analyzer_obj,
                indicators_obj = indicators_obj,
                asset_analyzer_obj = asset_analyzer_obj,
                stream_get_close = stream_manager_obj.get_close,
                record_obj = record_obj
            )

        # Call All stratagies         
        for idx in strategies_obj.get_id_list(): #run trough all the stratagies
            strategy = strategies_obj.get_by_id(idx)
            if not strategy.type_s == "AdvancedDCA" or not strategy.run: #run AdvancedDCA strategy only
                continue
            if not isinstance(idx, int):
                continue
            pair = f"{strategy.symbol1}{strategy.symbol2}"
            id_pair = f"{idx}_{pair}"
                        
            if not stream_manager_obj.all_streams_available(): #check if ther is any data from stream                    
                logger.error(f"strategy_run() error: No price data for ALL")
                break
            if pair not in stream_manager_obj.get_active_list(): #Check if the pair exists
                logger.error(f"strategy_run() error: No price data for {pair} ")
                continue
            if not stream_manager_obj.data_current(pair, 180): #check the data is not older than 3 min
                last_stream = stream_manager_obj.get_full(pair)
                if not last_stream:
                    time_last = 0
                else:
                    time_last = int(last_stream.time_ms / 1000)                
                logger.error(f"strategy_run() error: Old price data for {pair} {datetime.fromtimestamp(int(time_last))}")     
                continue           
            
            new_close = stream_manager_obj.get_close(pair)
            trade = dac_strategy.get_trade(idx)

            # This can be later moved to history thread
            market_history_obj.update_last(pair,new_close)

            # Trade manager calls for executing trades
            if trade:
                trade_manager_obj.new_trade(idx, trade)
                record_obj.reset(id_pair, new_close)
                record_obj.save()
                
            # Check for open trades
            open_trade = trade_manager_obj.get_open(idx)
            if open_trade:
                close_trade = ws_manager_obj.send_trade(open_trade)
                round_order = ws_manager_obj.get_pair_order_precision(pair)
                send_telegram_msg(_format_telegram_msg(open_trade, round_order))
                if close_trade:
                    trade_manager_obj.set_close(idx, close_trade)
                    send_telegram_msg(_format_telegram_msg(close_trade, round_order))
                asset_manager_obj.update(ws_manager_obj.fetch_user_data())

    except Exception as e: 
        logger.error(f"strategy_run() error: {e}")

def _format_telegram_msg(trade: Trade, round_order = 5):   
    try: 
        pair =  f"{trade.symbol1} / {trade.symbol2}"
        if float(trade.quantity1) < 0.0:
            side="SELL"
        else:
            side="BUY"
        if trade.commision > 0:
            append = f"commision = {round(trade.commision,6)} of {trade.commision_symbol} "
            title = ("Order FILLED :\n "
                        f"id : {trade.idx} \n "
                    )
        else:
            append = ""
            title = "New order send to exchange \n "
        
        telegram_msg = (f"{title} "
                            f"time : {datetime.fromtimestamp(int(trade.timestamp/1000))} \n "
                            f"side : {side} \n "
                            f"trading pair : {pair} \n "
                            f"quantity = {round(trade.quantity1,round_order)} of {trade.symbol1} \n "
                            f"quantity = {round(trade.quantity2,round_order)} of {trade.symbol2} \n "
                            f"at price = {abs(trade.price)} {trade.symbol2} \n "
                            f"change = {round(trade.change,2)} % \n "
                            f"{append} \n "
                            )
        return telegram_msg
    except Exception as e: 
        logger.error(f"format_telegram_msg() error: {e}")

def shut_down():
    """At application shut down save local values to files"""
    record_obj.save()
    strategies_obj.save()

