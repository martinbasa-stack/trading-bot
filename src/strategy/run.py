from..constants import(
    LOG_PATH_STRATEGY,
    FILE_PATH_HIST_STRATEGY,
    FILE_PATH_FEAR_GREAD
)
from src.binance import stream_manager_obj, ws_manager_obj #send_trade, fetch_user_data, fetch_kline, 
from src.settings import settings_obj, strategies_obj
from ..market_history import market_history_obj
from .trades import trade_manager_obj, Trade, TradeAnalyzer
from .assets import AssetAnalyzer, asset_manager_obj
from .indicators import IndicatorCompute
from .record_HL.manager import HLRecordManager
from .fear_gread.fear_gread import FearAndGread
from src.telegram import send_telegram_msg

from .dca import DCAstrategy

import logging
from datetime import datetime, timezone


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
fear_gread_obj = FearAndGread(path=FILE_PATH_FEAR_GREAD)

def _update_hist():
    logger.debug(f"Fetching historical data")    
    try:     
        #Fetch historical data for all pairs and needed intervals                
        interval_list = market_history_obj.get_list_to_update()
        if not interval_list:
            interval_list = strategies_obj.generate_pairs_intervals() 

        for _, info in interval_list.items():
            for interval in info["Intervals"]:
                s1 = info["Symbol1"]
                s2 = info["Symbol2"]
                #call function 
                kline_data = ws_manager_obj.fetch_kline(
                    symbol1=s1,
                    symbol2=s2,
                    interval=interval,
                    num_data=settings_obj.get("numOfHisCandles")                                     
                    )   
                #Save to local data
                if kline_data:
                    market_history_obj.update_interval(s1,s2,interval,kline_data) #Update data
        #Read user data
        asset_manager_obj.update(ws_manager_obj.fetch_user_data())

    except Exception as e: 
        logger.error(f"_update_hist() error: {e}")

#Call the strategies -------------------------------------------------------------------------------------------
def strategy_run():
    """Main strategy run logic and trade execution."""
    try:        
        fear_gread = fear_gread_obj.get() #update Fear and Gread index

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
            fear_gread=fear_gread.value
            )
        asset_analyzer_obj = AssetAnalyzer(
            get_by_id=strategies_obj.get_by_id,
            get_all_avg=trade_analyzer_obj.get_all_avgs,
            get_available_balance=asset_manager_obj.get_available,
            get_close=stream_manager_obj.get_close
        )
        #Call cleenup and run checks
        record_obj.cleanup()
        #Run history manager returns true if history files need update
        update_history = market_history_obj.run()                

        trade_manager_obj.cleanup()
        # Fetch history data
        if update_history:
            _update_hist()

        dac_strategy = DCAstrategy(
                strategies_obj=strategies_obj,
                trade_analyzer_obj = trade_analyzer_obj,
                indicators_obj = indicators_obj,
                asset_analyzer_obj = asset_analyzer_obj,
                stream_manager_obj = stream_manager_obj,
                record_obj = record_obj,
                market_history_obj = market_history_obj,
                log_path = LOG_PATH_STRATEGY      
            )

        # Call All stratagies         
        for idx in strategies_obj.get_id_list(): #run trough all the stratagies
            strategy = strategies_obj.get_by_id(idx)
            if not strategy.type_s == "AdvancedDCA" or not strategy.run: #run AdvancedDCA strategy only
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

            # Trade manager calls for executing trades
            if trade:
                print(f"New trade {trade}")
                trade_manager_obj.new_trade(idx, trade)
                record_obj.reset(id_pair, new_close)
            # Check for open trades
            open_trade = trade_manager_obj.get_open(idx)
            if open_trade:
                print(f"open_trade {open_trade}")
                close_trade = ws_manager_obj.send_trade(open_trade)
                round_order = ws_manager_obj.get_pair_order_precision(pair)
                send_telegram_msg(_format_telegram_msg(open_trade, round_order))                
                print(f"close_trade {close_trade}")
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
                            f"{append} \n "
                            )
        return telegram_msg
    except Exception as e: 
        logger.error(f"format_telegram_msg() error: {e}")

def shut_down():
    """At application shut down save local values to files"""
    record_obj.save()
    strategies_obj.save()

