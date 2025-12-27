from .price.manager import MarketHistoryManager
from .fear_gread.fear_gread import FearAndGread

from src.settings.main import strategies_obj, settings_obj
from src.constants import FILE_PATH_FEAR_GREAD
from src.binance.stream.thread import ws_manager_obj
from src.pyth.main import pyth_data_obj


import logging
import asyncio

market_binance_hist_obj = MarketHistoryManager(get_pairs_intervals=strategies_obj.generate_pairs_intervals,
                                          settings_get=settings_obj.get,
                                          provider="Binance"                                          
                                          )
market_pyth_hist_obj = MarketHistoryManager(get_pairs_intervals=strategies_obj.generate_pairs_intervals,
                                          settings_get=settings_obj.get,
                                          provider="DEX"                                          
                                          )

fear_gread_obj = FearAndGread(path=FILE_PATH_FEAR_GREAD,
                              get_settings=settings_obj.get
                              )


# self._logger
# ----------------------------------------------------------------------
logger = logging.getLogger("app").getChild(__name__)

async def _from_binance(s1, s2, interval ,num_data):
    if ws_manager_obj.check_pair_exist(f"{s1}{s2}"):
        return ws_manager_obj.fetch_kline(
            symbol1=s1,
            symbol2=s2,
            interval=interval,
            num_data=num_data
            )
    
    return None
    
async def _from_pyth(s1, s2, interval ,num_data):
    d = pyth_data_obj.fetch_kline(
        s1=s1,
        s2=s2,
        interval=interval,
        num_data=num_data
        )
    return d

async def _update_hist(hist_obj :  MarketHistoryManager, func_retrive : callable ):
    logger.debug(f"Fetching historical data for {hist_obj.provider}")    
    try:     
        #Fetch historical data for all pairs and needed intervals                
        interval_list = hist_obj.get_list_to_update()
        if not interval_list:
            interval_list = strategies_obj.generate_pairs_intervals(hist_obj.provider) 
        
        num_data = settings_obj.get("numOfHisCandles") 
        kline_data = None
        for _, info in interval_list.items():
            for interval in info["Intervals"]:
                s1 = info["Symbol1"]
                s2 = info["Symbol2"]
                
                kline_data = await func_retrive(s1, s2, interval ,num_data)
                #Save to local data
                if kline_data is not None:
                    hist_obj.update_interval(s1,s2,interval,kline_data) #Update data
                    await asyncio.sleep(0.01)

    except Exception as e:         
        logger.error(f"_update_hist() error: {e}")


async def history_run():
    """Main history data managment."""

    #Call cleenup and run checks
    fear_gread_obj.run()
    #Run history manager returns true if history files need update
    update_hist_b = market_binance_hist_obj.data_update_req()
    update_hist_p = market_pyth_hist_obj.data_update_req()             

    # Fetch history data
    if update_hist_b:
        await _update_hist(market_binance_hist_obj, _from_binance)

    if update_hist_p:
        await _update_hist(market_pyth_hist_obj, _from_pyth)