from .models import Trade, PnL, AverageSum
from src.market_history import IntervalData
from ..record_HL.models import HLRecord

from src.settings import StrategyConfig

from datetime import datetime, timezone
from typing import Tuple 
import threading
import logging

import talib as ta

# TradeAnalyzer Class (short-living)
# ----------------------------------------------------------------------
class TradeAnalyzer:
    """ (short-living) Class for analayzing trades from trade tables """
    def __init__(self, 
                 get_by_id :callable,
                 get_trade_table:callable, 
                 get_hist_table:callable
                 ):     
        """ 
        Args:
            get_by_id(callable(id)):
                get all strategy parameters by ID from StrategyManager /settings
            get_trade_table(callable(id)):
                get a teble of trades by ID from TradeManager class /trades
            get_hist_table(callable(pair, interval)):
                get kLine historical data of pair and interval from MarketHistoryManager /market_history
        """
        self._get_trade_table :callable = get_trade_table
        self._get_hist_table :callable = get_hist_table
        self._get_by_id :callable = get_by_id
        self._pair: str = ""
        self._strategy: StrategyConfig = None
        #threding
        self._lock = threading.RLock()
        
        # --- Logger Setup ---
        self._logger = logging.getLogger("strategy").getChild(self.__class__.__name__)

    # Public 
    # ==================================================================
    # Get Profit/Loss from trade table 
    # ------------------------------------------------------------------
    def get_pnl(self, strategy_id:int, last_close:float) -> PnL:
        """
        Args:
            strategy_id(int): 
                strategy IDx

            last_close(float):
                last price for calculating unrealized PnL

        Returns:
           PnL:
                DataClass of PNL 
        """
        try:
            with self._lock:
                self._fetch_strategy_data(strategy_id) # First load data!
                result_list, _ = self._averadge_cost_pnl(strategy_id, last_close)
                return result_list[-1]
        except Exception as e:
            self._logger.error(f"TradeAnalyzer get_pnl() error: {e}")
    
    # Get one avg cost/entr/exit and sum of all trades in the trade table 
    # ------------------------------------------------------------------
    def get_single_avg(self, strategy_id:int, selector = "cost") -> AverageSum:
        """
        Args:
            strategy_id(int): 
                strategy IDx

            selector(str, optional):
                value options "cost", "entry", "exit"

        Returns:
           AverageSum:
                Selected value, default is "cost" 
        """
        try:
            with self._lock:
                self._fetch_strategy_data(strategy_id) # First load data!

            result_list = self.get_single_avg_list(strategy_id, selector)

            with self._lock:
                return result_list[-1]
        except Exception as e:
            self._logger.error(f"TradeAnalyzer get_single_avg() error: {e}")
        
    # Get one avg cost/entr/exit and sum as list for every line in trade table
    # ------------------------------------------------------------------
    def get_single_avg_list(self, strategy_id:int, selector = "cost") -> list[AverageSum]:
        """
        Args:
            strategy_id(int): 
                strategy IDx

            selector(str, optional):
                value options "cost", "entry", "exit"

        Returns:
           list[AverageSum]:
                Selected value, default is "cost" 
        """
        try:
            with self._lock:
                self._fetch_strategy_data(strategy_id) # First load data!
                match selector:
                    case "exit":
                        result_list = self._avg_sum(strategy_id, exit=True)
                    case "entry":
                        result_list = self._avg_sum(strategy_id)
                    case _:
                        _, result_list = self._averadge_cost_pnl(strategy_id, 0)

                return result_list
        except Exception as e:
            self._logger.error(f"TradeAnalyzer get_single_avg_list() error: {e}")
    
    # Get all avg cost/entr/exit and sum of all trades in the trade table 
    # ------------------------------------------------------------------
    def get_all_avgs(self, strategy_id:int) -> Tuple[AverageSum, AverageSum, AverageSum]:
        """
        Args:
            strategy_id(int): 
                strategy IDx

        Returns:
           Tuple [AverageSum, AverageSum, AverageSum]:
                entry, cost, exit               
        """     
        try:   
            with self._lock:
                self._fetch_strategy_data(strategy_id) # First load data!

            entry_list, cost_list, exit_list = self.get_all_avgs_list(strategy_id)

            with self._lock:            
                return entry_list[-1], cost_list[-1], exit_list[-1]
        except Exception as e:
            self._logger.error(f"TradeAnalyzer get_all_avgs() error: {e}")
        
    # Get all avg cost/entr/exit and sum as list for every line in trade table
    # ------------------------------------------------------------------
    def get_all_avgs_list(self, strategy_id:int) -> Tuple[list[AverageSum], list[AverageSum], list[AverageSum]]:
        """
        Args:
            strategy_id(int): 
                strategy IDx

        Returns:
           Tuple [list[AverageSum], list[AverageSum], list[AverageSum]]:
                entry_list, cost_list, exit_list             
        """
        try:
            with self._lock:
                self._fetch_strategy_data(strategy_id) # First load data!
                entry_list = self._avg_sum(strategy_id)
                _, cost_list = self._averadge_cost_pnl(strategy_id, 0)
                exit_list = self._avg_sum(strategy_id, exit=True)
    
                return entry_list, cost_list, exit_list
        except Exception as e:
            self._logger.error(f"TradeAnalyzer get_all_avgs_list() error: {e}")
    
    # Get min max price after last trade
    # ------------------------------------------------------------------   
    def get_min_max_price(self, strategy_id, record: HLRecord) -> Tuple[float, float]:
        """
        Args:
            strategy_id(int): 
                strategy IDx

            record(HLRecord): 
                data from HighLowRecordManager

        Returns:
            Tuple[float, float]:
                min_price, max_price                
        """
        try:
            with self._lock:            
                lookback=self.get_kline_id_of_last_trade(strategy_id) #This call allso fills the local self. vars
                last_trade_price = self._last_trade_price(strategy_id)
                min_price, max_price = self._min_max_price(last_trade_price,lookback, record)
                
                return min_price, max_price
        except Exception as e:
            self._logger.error(f"TradeAnalyzer get_min_max_price() error: {e}")
    
    # Get look back value the id of when the last trade happend 0 -> in the activ candle 
    # ------------------------------------------------------------------
    def get_kline_id_of_last_trade(self, strategy_id) -> int:
        """
        Args:
            strategy_id(int): 
                strategy IDx

        Returns:
            int:
                loockback -> index of candle where last trade was made                
        """
        try:
            with self._lock:
                self._fetch_strategy_data(strategy_id) # First load data!
                trade_table: list[Trade] = self._get_trade_table(strategy_id)
                if not trade_table:
                    return self._strategy.lookback
                hist_table:IntervalData = self._hist_table()
                if not hist_table:
                    return self._strategy.lookback
                arr = hist_table.time_open
                reverse = arr[::-1]
                trade_time = trade_table[-1].timestamp
                for idx, time_open in enumerate(reverse):
                    if time_open < trade_time:
                        return idx
                return idx 
        except Exception as e:
            self._logger.error(f"TradeAnalyzer get_kline_id_of_last_trade() error: {e}")
    
    # get trade enable time lock 
    # ------------------------------------------------------------------
    def get_trade_enable(self, strategy_id) -> bool:
        """
        Args:
            strategy_id(int): 
                strategy IDx

        Returns:
            bool:
                trade enable trigger                
        """   
        try:
            with self._lock:
                hist_table:IntervalData = self._hist_table()
                if not hist_table:
                    return False
                time_open = hist_table.time_open[-1]        
                self._fetch_strategy_data(strategy_id)
                enable = True
                if self._strategy.candle_close_only:
                    enable = self._check_candle_close(int(time_open))
                
                trade_table: list[Trade] = self._get_trade_table(strategy_id)
                if not trade_table:
                    return enable
                now_seconds = self._now()
                trade_time = trade_table[-1].timestamp
                if self._strategy.time_limit_new_order < int(now_seconds - trade_time):
                    return enable
                return enable 
        except Exception as e:
            self._logger.error(f"TradeAnalyzer get_trade_enable() error: {e}")

    # Helpers
    # ==================================================================
    # get array of close time from marked data history self.pair,self.interval!
    # ------------------------------------------------------------------
    def _hist_table(self) -> IntervalData:    
        hist_table : IntervalData = self._get_hist_table(self._pair,self._strategy.candle_interval)        
        return hist_table
    
    def _check_candle_close(self,time_open) -> bool:
        now_seconds = self._now()
        last_open = int(time_open/1000)
        return int(now_seconds - last_open) < int(self._strategy.time_limit_new_order*0.9)
    # get data from strategy and save to local vars
    # ------------------------------------------------------------------
    def _fetch_strategy_data(self, strategy_id):
        strategy : StrategyConfig = self._get_by_id(strategy_id)
        if not strategy:
            return
        self._pair = f"{strategy.symbol1}{strategy.symbol2}"
        self._strategy = strategy
  
    # get last trade price
    # ------------------------------------------------------------------  
    def _last_trade_price(self, strategy_id) -> float:
        trade_table: list[Trade] = self._get_trade_table(strategy_id)
        if not trade_table:
            return 0
        return trade_table[-1].price

    # logic for determaning min and max price
    # ------------------------------------------------------------------
    def _min_max_price(self, last_trade_price, lookback, record: HLRecord) -> Tuple[float, float]: 
        hist_table: IntervalData = self._hist_table()
        high = hist_table.high
        low = hist_table.low   
        lookback = lookback % len(high) # Limit index
        if lookback < 1: #Trade in the last candle #Save to dictionary maximum FOR BUY
            max_price = max(last_trade_price, record.high)# Need check if the price went above    
            min_price = min(last_trade_price, record.low) # Check if the price went below
        elif 0 < lookback < self._strategy.lookback:#Trade was done one candle ago and les than selected lookback              
            #Write last trade price to the TA anlasys arry to use it insted of actual value
            high[len(high)-1 -lookback] = max(record.high ,last_trade_price)
            #Write last trade price to the TA anlasys arry to use it insted of actual value
            low[len(low)-1 -lookback] = min(record.low, last_trade_price)  #Write last trade price to the TA anlasys arry to use it insted of actual value
            maxK = ta.MAX(high,lookback+1) #Using lenght +1 to use the price that was added to array so it will compare current candle with price before
            max_price = maxK[-1]                
            minK = ta.MIN(low,lookback+1)  
            min_price = minK[-1]              
        else: #Trade was done more than "NumOfCandlesForLookback" candles ago ta will get min and max                
            lookback = self._strategy.lookback
            maxK = ta.MAX(high,lookback)
            max_price = maxK[-1]
            minK = ta.MIN(low,lookback)
            min_price = minK[-1]
        return float(min_price), float(max_price)
    # generate sum and avg of exit or entry trades
    # ------------------------------------------------------------------
    def _avg_sum(self, strategy_id:int, exit: bool = False) -> list[AverageSum]:
        avg_list : list[AverageSum] = []
        trade_table: list[Trade] = self._get_trade_table(strategy_id)
        if not trade_table:
            return AverageSum()
        sum1= 0
        sum2= 0
        num = 0
        for trade in trade_table:        
            if trade.quantity1 < 0 and not exit: #Positive is entry
                continue
            if trade.quantity1 > 0 and exit: #Negative is exit
                continue
            sum1 += abs(trade.quantity1)
            sum2 += abs(trade.quantity2)
            num +=1
            avg_calc = sum2/ sum1 if sum1 !=0 else 0
            avg_list.append(AverageSum(avg=avg_calc, sum1=sum1, sum2=sum2, num=num))

        return avg_list
    
    # generate sum, avg and calculate Profit/Loss of all trades ChatGpt build it :)
    # ------------------------------------------------------------------
    def _averadge_cost_pnl(self, strategy_id:int, last_close) -> Tuple[list[PnL],  list[AverageSum]]:
        trade_table: list[Trade] = self._get_trade_table(strategy_id)        
        avg_list : list[AverageSum] = []  
        pnl_list : list[PnL] = []
        if not trade_table:
            return pnl_list.append(PnL()), avg_list.append(AverageSum())
        position = 0.0        # net S1  position, signed
        cost_basis = 0.0      # absolute S2 that backs the position (>= 0)
        realized_pnl = 0.0
        sum1 = 0
        sum2 = 0
        num = 0
        for trade in trade_table:        
            qty_S1 = trade.quantity1  # S1 amount (signed)
            qty_S2 = trade.quantity2  # S2 amount (signed)
            sum1 += qty_S1
            sum2 += qty_S2
            num +=1
            # Opening when flat
            if position == 0:
                position = qty_S1
                cost_basis = abs(qty_S2)
                continue

            # Are we adding to the current side or reducing it?
            same_side = (position > 0 and qty_S1 > 0) or (position < 0 and qty_S1 < 0)
            # avg cost per unit (always positive)
            avg_cost = cost_basis / abs(position) if position != 0 else 0.0

            if same_side:
                # increase existing position: add absolute S2 to cost_basis
                position += qty_S1
                cost_basis += abs(qty_S2)
            else:
                # reducing (or closing + flipping)
                reduce_amount = min(abs(qty_S1), abs(position))
                removed_cost = reduce_amount * avg_cost                       # S2 removed from cost basis
                proceeds = abs(qty_S2) * (reduce_amount / abs(qty_S1))            # S2 corresponding to the closed portion

                # realized PnL depends on whether we closed a long or closed a short
                if position > 0 and qty_S1 < 0:
                    # closing long: we sold now -> realized = proceeds - removed_cost
                    realized_pnl += proceeds - removed_cost
                elif position < 0 and qty_S1 > 0:
                    # closing short: we bought now -> realized = removed_cost - proceeds
                    realized_pnl += removed_cost - proceeds
                else:
                    # defensive — should not occur
                    pass

                # remove cost from basis, update position
                cost_basis -= removed_cost
                position += qty_S1

                # fully closed
                if position == 0:
                    cost_basis = 0.0
                else:
                    # If the trade had a remainder that opens a new position
                    # remaining_usdc = abs(usdc) - proceeds  (>= 0)
                    # this remaining USDC becomes the new cost basis for the new side
                    if (position > 0 and qty_S1 > 0) or (position < 0 and qty_S1 < 0):
                        remaining_usdc = abs(qty_S2) - proceeds
                        cost_basis = remaining_usdc
            avg_cost = cost_basis / abs(position) if position != 0 else 0.0
            avg_list.append(AverageSum(avg=avg_cost, sum1=sum1, sum2=sum2, num=num))
            # finalize avg cost and unrealized        
            if position > 0:
                unrealized_pnl = position * (last_close - avg_cost)
            elif position < 0:
                unrealized_pnl = abs(position) * (avg_cost - last_close)
            else:
                unrealized_pnl = 0.0
            total_pnl = unrealized_pnl+realized_pnl
            unreal_percent=unrealized_pnl / abs(cost_basis) * 100 if cost_basis != 0 else 0
            real_percent=realized_pnl / abs(cost_basis) * 100 if cost_basis != 0 else 0
            total_percent=total_pnl / abs(cost_basis) * 100 if cost_basis != 0 else 0

            pnl_list.append( PnL(
                realised=realized_pnl,
                real_percent=real_percent,
                unrealised=unrealized_pnl,
                unreal_percent=unreal_percent,
                total=total_pnl,
                total_percent=total_percent
            ))
        return pnl_list, avg_list
    
    @staticmethod
    def _now():        
        now_utc = datetime.now(timezone.utc)
        return int(now_utc.timestamp())       