from .models import TriggerComputeResult
from .trades import TradeAnalyzer, Trade
from .indicators import IndicatorCompute
from .assets import AssetManagerResult, AssetAnalyzer
from .record_HL.manager import HLRecordManager 

from src.settings import StrategyManager

import copy
import threading
import logging 
from datetime import datetime, timezone

class DCAstrategy:    
    """ 
    (short-living) computing strategy data from other objects
    """
    def __init__(self, 
                 strategies_obj : StrategyManager, 
                 trade_analyzer_obj : TradeAnalyzer,
                 indicators_obj : IndicatorCompute,
                 asset_analyzer_obj : AssetAnalyzer,
                 stream_get_close: callable,
                 record_obj : HLRecordManager,
                 ):  
        """ 
        Args:
            strategies_obj(StrategyManager)): 
                Object in /settings
            
            trade_analyzer_obj (TradeAnalyzer):
                Object in ./trades
            indicators_obj(IndicatorCompute):
                Object in ./indicators
            asset_analyzer_obj(AssetAnalyzer):
                Object in ./assets
            stream_get_close(callable):
                Get las price
            record_obj(HLRecordManager):
                Object in ./record_HL
            market_history_obj(MarketHistoryManager):
                Object in /market_history
        """
        # get_pairs_intervals is a function get_pairs_intervals() from another class
        self._strategies_obj: StrategyManager = strategies_obj
        self._trade_analyzer_obj: TradeAnalyzer = trade_analyzer_obj
        self._indicators_obj: IndicatorCompute = indicators_obj
        self._asset_analyzer_obj: AssetAnalyzer = asset_analyzer_obj
        self._stream_get_close: callable = stream_get_close
        self._record_obj : HLRecordManager = record_obj

        self._new_close : float = 0.0
        self._buy_factor : float = 0.0
        self._sell_factor : float = 0.0
        self._asset_result : AssetManagerResult = None
        self._compute_result : TriggerComputeResult = None

        self._lock = threading.Lock()

        # self._logger
        # ----------------------------------------------------------------------
        self._logger = logging.getLogger("strategy").getChild(self.__class__.__name__)
    
    def get_trade(self, strategy_id: int) -> Trade:
        """ 
        Args:
            strategy_id(StrategyManager)): 
                ID of strategy
        Returns:
            Trade:
                condition:
                if triggers not true returns None  
        """
        with self._lock:
            if not self._compute(strategy_id):
                return None            
            return self._format_trade()

    def get_trigger_compute(self, strategy_id) -> TriggerComputeResult:  
        """ 
        Args:
            strategy_id(StrategyManager)): 
                ID of strategy
        Returns:
            TriggerComputeResult:
                Returns resaults of all triggers and object computes
        """
        with self._lock:      
            if not self._compute(strategy_id):
                return None
            return copy.copy(self._compute_result)

    def _compute(self, idx):
        try:
            if idx not in self._strategies_obj.get_id_list():
                return None
            self._strategy = self._strategies_obj.get_by_id(idx)
            
            pair = f"{self._strategy.symbol1}{self._strategy.symbol2}"
            id_pair = f"{idx}_{pair}"
            #Update price data 
            self._new_close = self._stream_get_close(pair) #get close price
            if self._new_close == 0:
                return None
            #self._market_history_obj.update_last(pair,self._new_close)
            self._record_obj.update(id_pair, self._new_close)
            # Get min max price
            min_price, max_price = self._trade_analyzer_obj.get_min_max_price(idx, self._record_obj.get(id_pair))
            trade_enable = self._trade_analyzer_obj.get_trade_enable(idx)

            #Compute indicator values
            buy_factor, buy_weight, buy_ind_trade_en = self._indicators_obj.get_buy_compute(idx)
            sell_factor, sell_weight, sell_ind_trade_en = self._indicators_obj.get_sell_compute(idx)
            #Asset managment
            self._asset_result : AssetManagerResult = self._asset_analyzer_obj.get_compute(idx, buy_factor, sell_factor) 

            #Check changes form Max newBuyDropOk
            percent_change_dip = (max_price - self._new_close) / max_price * 100  if max_price != 0 else 0
            dca_buy_trigger = percent_change_dip > self._strategy.asset_manager.dip_buy
            #Check changes form Min newSellPumpOk
            percent_change_pump = (self._new_close - min_price) / min_price * 100 if min_price != 0 else 0
            dca_sell_trigger = percent_change_pump > self._strategy.asset_manager.pump_sell

            # if both are triggered select only the one that is not to be saved
            if dca_buy_trigger and dca_sell_trigger:
                if self._strategy.asset_manager.target != "None":
                    if self._strategy.asset_manager.symbol_index == 1:
                        dca_sell_trigger = False
                    else:
                        dca_buy_trigger =  False
                        
            lookback = self._trade_analyzer_obj.get_kline_id_of_last_trade(idx)

            self._compute_result= TriggerComputeResult(
                strategy_idx = idx,
                trade_enable = trade_enable,
                lookback=lookback,

                buy_sum_trigger = trade_enable and buy_ind_trade_en and dca_buy_trigger and self._asset_result.s2_balance_ok,
                buy_ind_trade_en = buy_ind_trade_en,            
                buy_weight  = buy_weight,
                buy_factor  = buy_factor,
                dca_buy_trigger = dca_buy_trigger,
                percent_change_dip = percent_change_dip,
                min_price  = min_price,
            
                sell_sum_trigger  = trade_enable and sell_ind_trade_en and dca_sell_trigger and self._asset_result.s1_balance_ok,
                sell_ind_trade_en  = sell_ind_trade_en,    
                sell_weight  = sell_weight,
                sell_factor  = sell_factor,
                dca_sell_trigger = dca_sell_trigger,
                percent_change_pump = percent_change_pump,
                max_price = max_price
            )
            
            return True
        except Exception as e:
            self._logger.error(f"DCA compute error: {e}")
            
    def _format_trade(self) -> Trade:  
        try:   
            now_seconds = self._now()

            idx= self._strategy.idx
            s1 = self._strategy.symbol1
            s2 = self._strategy.symbol2
            id_pair = f"{idx}_{s1}{s2}"

            #Paper trade id
            if self._strategy.asset_manager.paper_t: 
                trade_id = "Paper"
            else:
                trade_id = "Open"        
            #----------------------Format trade----------------------------
            commission = 0.0 
            commission_asset = "NaN"  
            trigger_buy = self._compute_result.buy_sum_trigger
            trigger_sell = self._compute_result.sell_sum_trigger

            #Buy conditions
            if (trigger_buy):
                s1_qt = self._asset_result.to_buy/self._new_close
                s2_qt = -round(self._asset_result.to_buy, self._strategy.round_order)
                percent_change = self._compute_result.percent_change_dip
                side = "BUY"
            #Sell conditions
            elif (trigger_sell):            
                s1_qt = -self._asset_result.to_sell/self._new_close
                s2_qt = round(self._asset_result.to_sell, self._strategy.round_order)
                percent_change = self._compute_result.percent_change_pump
                side = "SELL"

            trade = None

            avg_cost = self._trade_analyzer_obj.get_single_avg(idx).avg
            #Write trade to table
            if trigger_buy or trigger_sell:
                #Format trade
                trade: Trade = Trade(
                        timestamp=now_seconds*1000,
                        idx= trade_id,
                        symbol1= s1,
                        quantity1= s1_qt,
                        symbol2= s2,
                        quantity2= s2_qt,
                        price= self._new_close,
                        max_p= self._compute_result.max_price,
                        min_p= self._compute_result.min_price,
                        lookback= self._compute_result.lookback,
                        avg_cost= avg_cost,
                        change= percent_change,
                        commision= commission,
                        commision_symbol= commission_asset
                    )
                
                self._record_obj.reset(id_pair, self._new_close)

                if not self._strategy.asset_manager.paper_t and idx !="backtester":                    
                    self._logger.info(f"New {side} order at : {datetime.fromtimestamp(int(now_seconds))} \n "
                                f"strategy id : {idx} \n "
                                f"pair : {s1}/{s2} \n "
                                f"{side} : {s1_qt} {s1} \n "
                                f"for : {s2_qt} {s2} \n "
                                f"at price : {self._new_close} ")
        
            # Wrtite status to logger 
            self._logger.debug(f"Strategy id {idx} \n {self._strategy.name} on {s1}/{s2} pair \n"
                        f"last price: {self._new_close}; \n Avrage cost: {avg_cost}; \n Lookback val: {self._compute_result.lookback}"
                        )        
            return trade
        except Exception as e:
            self._logger.error(f"DCA format trade error: {e}")
    
        # ------------------------------------------------------------------
    @staticmethod
    def _now():        
        now_utc = datetime.now(timezone.utc)
        return int(now_utc.timestamp())     

