from .price.manager import MarketHistoryManager
from .fear_gread.fear_gread import FearAndGread

from src.settings import strategies_obj, settings_obj
from src.constants import FILE_PATH_FEAR_GREAD
from src.binance import ws_manager_obj
from src.strategy import asset_manager_obj

import logging
import time

market_history_obj = MarketHistoryManager(get_pairs_intervals=strategies_obj.generate_pairs_intervals,
                                          settings_get=settings_obj.get                                          
                                          )



fear_gread_obj = FearAndGread(path=FILE_PATH_FEAR_GREAD,
                              get_settings=settings_obj.get
                              )


# self._logger
# ----------------------------------------------------------------------
logger = logging.getLogger("app").getChild(__name__)


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
                    time.sleep(0.01)
        #Read user data
        asset_manager_obj.update(ws_manager_obj.fetch_user_data())

    except Exception as e:         
        logger.error(f"_update_hist() error: {e}")


def history_run():
    """Main history data managment."""

    #Call cleenup and run checks
    fear_gread_obj.run()
    #Run history manager returns true if history files need update
    update_history = market_history_obj.run()                

    # Fetch history data
    if update_history:
        _update_hist()