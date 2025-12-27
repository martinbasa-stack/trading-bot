from..constants import(
    LOG_PATH_STRATEGY
)

from src.settings.main import strategies_obj
from src.settings.models import StrategyConfig
from src.telegram.main import telegram_obj
from src.binance.websocket.thread import ws_manager_obj
from src.models import Trade
from src.assets.main import update_assets_q
from src.solana_api.main import solana_man_obj

from .trades.main import trade_manager_obj
from .record_HL.main import record_obj
from .utils import build_objects

import logging
from datetime import datetime, timezone
import asyncio

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

#Call the strategies -------------------------------------------------------------------------------------------
async def strategy_run():
    """
    Main strategy run logic and trade execution.
    Call only if all data is available!
    """
    try:
        #Call cleenup and run checks
        record_obj.cleanup()
        trade_manager_obj.cleanup()

        # Call All stratagies         
        for idx in strategies_obj.get_id_list(): #run trough all the stratagies
            s = strategies_obj.get_by_id(idx)
            if not s.run:
                continue
            if not isinstance(idx, int): # ID has to be an intiger
                continue
            if "Raydium" in s.type_s and solana_man_obj.locked:
                continue
            pair = f"{s.symbol1}{s.symbol2}"
            id_pair = f"{idx}_{pair}"

            _, _, _, dac_strategy, hist_obj, get_close = build_objects(s.type_s, record_obj)                        
            
            new_close = get_close(pair)
            trade = dac_strategy.get_trade(idx)

            # This can be later moved to history thread
            hist_obj.update_last(pair,new_close)

            # Trade manager calls for executing trades
            if trade:
                trade_manager_obj.new_trade(idx, trade)
                record_obj.reset(id_pair, new_close)
                record_obj.save()
                
            # Trade executions
            if "Binance" in s.type_s:
                await _trade_on_binance(s)
            elif "Raydium" in s.type_s:
                await _trade_on_raydium(s)            

    except Exception as e: 
        logger.error(f"strategy_run() error: {e}")

async def _trade_on_raydium(s: StrategyConfig):
    if s.asset_manager.paper_t:
        return
    open_trade = trade_manager_obj.get_open(s.idx)        

    if open_trade:
        send_trade = solana_man_obj.send_trade(s.idx, open_trade, 1.0)
        if send_trade:
            await asyncio.sleep(0.5)
            telegram_obj.send_msg(_format_telegram_msg(send_trade, "Raydium"))

    close_trade = solana_man_obj.is_trade_closed(s.idx)

    if close_trade:        
        trade_manager_obj.set_close(s.idx, close_trade)
        solana_man_obj.remove(s.idx)
        update_assets_q("Solana")
        telegram_obj.send_msg(_format_telegram_msg(close_trade, "Raydium"))
    

async def _trade_on_binance(s:StrategyConfig):
    if s.asset_manager.paper_t:
        return
    open_trade = trade_manager_obj.get_open(s.idx)
    if open_trade:
        close_trade = ws_manager_obj.send_trade(open_trade)
        round_order = ws_manager_obj.get_pair_order_precision(f"{s.symbol1}{s.symbol2}")
        telegram_obj.send_msg(_format_telegram_msg(open_trade, "Binance" , round_order))
        if close_trade:
            trade_manager_obj.set_close(s.idx, close_trade)            
            telegram_obj.send_msg(_format_telegram_msg(close_trade, "Binance" , round_order))
        update_assets_q("Binance")

def _format_telegram_msg(trade: Trade, exchange : str, round_order = 5):   
    try: 
        pair =  f"{trade.symbol1} / {trade.symbol2}"
        if float(trade.quantity1) < 0.0:
            side="SELL"
        else:
            side="BUY"
        if trade.commision > 0:
            append = f"commision = {round(trade.commision,6)} of {trade.commision_symbol} "
            title = (f"Order FILLED {exchange}:\n "
                        f"id : {trade.idx} \n "
                    )
        else:
            append = ""
            title = f"New order send to exchange {exchange} \n "
        
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

