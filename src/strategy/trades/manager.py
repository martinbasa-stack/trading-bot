from .models import TradeTable
from .storage import load_csv, save_csv, build_trade_path, delete_csv

from src.models import Trade
from src.settings import StrategyConfig, StrategyManager
from src.constants import(
    TRADE_TABLE_COL_TIMESTAMP,
    TRADE_TABLE_COL_ID,
    TRADE_TABLE_COL_SYMBOL_1,
    TRADE_TABLE_COL_ASSET_S1_QT,
    TRADE_TABLE_COL_SYMBOL_2,
    TRADE_TABLE_COL_ASSET_S2_QT,
    TRADE_TABLE_COL_PRICE,
    TRADE_TABLE_COL_MAX,
    TRADE_TABLE_COL_MIN,
    TRADE_TABLE_COL_LOOKBACK,
    TRADE_TABLE_COL_AVG_COST,
    TRADE_TABLE_COL_CHANGE,
    TRADE_TABLE_COL_COMMISION,
    TRADE_TABLE_COL_COMMISION_ASSET
)

from datetime import datetime, timezone
import copy
from typing import Dict
import threading
import logging

# TradeManager Class (long-living)
# ----------------------------------------------------------------------
class TradeManager:
    """ 
    (long-living) Class for storing and managin trades
        saving and loading from .csv files
    """
    def __init__(self, strategies_obj : StrategyManager, 
                 get_settings: callable
                 ):  
        """ 
        Args:
            strategies_obj(StrategyManager)): 
                object StrategyManager /settings

            get_settings(callalble(str)): 
                get setting value from SettingsManager /settings
        """
        # get_pairs_intervals is a function get_pairs_intervals() from another class
        self._strategies_obj: StrategyManager = strategies_obj
        self._get_settings = get_settings
        self._data: Dict[int, TradeTable] = {}  # TradeTables        
        # threading
        self._lock = threading.RLock()
        #At initialisation load all data 
        self._load_all()

        # --- Logger Setup ---
        self._logger = logging.getLogger("strategy").getChild(self.__class__.__name__)


    # Public 
    # ==================================================================
    # Update add new trade
    # ------------------------------------------------------------------
    def new_trade(self, strategy_id: int, trade :Trade, save_to_file = True): 
        """ 
        Write new trade to the table
        Args:
            strategy_id(int): 
                ID of a strategy for the trade
            trade(Trade):
                Trade to be writen to the table
            save_to_file(bool, optional):
                Selector to save new trade to file.
        """
        with self._lock:
            idx = strategy_id
            strategy : StrategyConfig = self._strategies_obj.get_by_id(idx)
            s1 = strategy.symbol1
            s2 = strategy.symbol2
            type_s = strategy.type_s
            #Build table if it does not exist
            
            if idx not in self._data:            
                self._set_table(strategy, True)

            #Save data localy
            if self._data[idx].paper:
                self._data[idx].paper_trades.append(trade)
                path = build_trade_path(s1,s2,idx,type_s,"Paper")
                trades = self._data[idx].paper_trades
            else:
                self._data[idx].trades.append(trade)
                path = build_trade_path(s1,s2,idx,type_s)
                trades = self._data[idx].trades

            #Save data to file
            if save_to_file:
                rows = self._trades_to_array(trades)    
                save_csv(path,rows)
        
    # Cleanup -> delete local data if no strategy and delete old Open Send trades
    # ------------------------------------------------------------------
    def cleanup(self):
        """ 
        Check if strategy was deleted than delet trading data of that strategy.
            Deleta old (Open, Send) trades from trade table.
        """
        try:
            with self._lock:
                strategies_ids = self._strategies_obj.get_id_list()
                for idx in list(self._data): #run trough list            
                    if idx not in strategies_ids: #If it does not exist remove it 
                        self.delete(idx, True)
                    else:# Remove Open Send trades that are to old
                        self._table_cleanup(idx)
        except Exception as e:
            self._logger.error(f"TradeManager cleanup() error: {e}")

    # Delete trading tables of strategy and local data optional
    # ------------------------------------------------------------------
    def delete(self, strategy_id: int, local=False): 
        """ 
        Delete all trade data local and from file .csv
        Args:
            strategy_id(int): 
                ID of a strategy to delete
            local(bool, optional):
                condition:
                if true the complete local TradeTable will be deleted.
        """
        try:
            with self._lock:
                idx = strategy_id
                if idx not in self._data: #If there is no table already 
                    return
                s1 = self._data[idx].symbol1
                s2 = self._data[idx].symbol2
                type_s = self._data[idx].type_s
                #Remove local data if selected
                if local: del self._data[idx]
                paths = [build_trade_path(s1,s2,idx,type_s,"Paper"),
                            build_trade_path(s1,s2,idx,type_s,)]
                delete_csv(paths) #remove files
        except Exception as e:
            self._logger.error(f"TradeManager delete() error: {e}")

    # Update datafrom strategy if strategy changed
    # ------------------------------------------------------------------
    def update(self, strategy_id:int):    
        """ 
        Update after strategy config was changed
        Args:
            strategy_id(int): 
                ID of a strategy
        """
        try:
            with self._lock:
                idx = strategy_id
                strategy: StrategyConfig = self._strategies_obj.get_by_id(idx)
                if strategy is None:
                    return
                if idx not in self._data: #Create new
                    self._set_table(strategy, True)
                    return
                s1 = strategy.symbol1
                s2 = strategy.symbol2
                pair = f"{s1}{s2}"
                if pair != self._data[idx].pair:
                    self.delete(idx)#Delete tables if new pair
                    self._set_table(strategy, True)#Inserting new table will clear trades
                else:
                    self._set_table(strategy, False)
        except Exception as e:
            self._logger.error(f"TradeManager update() error: {e}")

    # Find last open trade and send it -> localy mark as Send
    # ------------------------------------------------------------------
    def get_open(self, strategy_id) -> Trade:  
        """ 
        Get last open trade
        Args:
            strategy_id(int): 
                ID of a strategy

        Returns:
            Trade:
                Trade structure so send. Marks idx as "Send"
        """
        try:
            with self._lock:
                time_old_seconds = self._get_settings("liveTradeAging")
                idx = strategy_id
                #Table should be setup but still check
                if idx not in self._data: 
                    return None
                if self._data[idx].paper: #If paper trading do nothing
                    return None
                trades = self._data[idx].trades
                open_idx = self._get_last(trades, "Open")        
                if open_idx is None:
                    return None   
                if not self._check_trade_age_ok(idx, open_idx,time_old_seconds): #Trade to old
                    return None 
                #Write send to idx to mark it   
                self._data[idx].trades[open_idx].idx = "Send"

                return copy.deepcopy(self._data[idx].trades[open_idx])
        except Exception as e:
            self._logger.error(f"TradeManager get_open() error: {e}")
    
    # Find last send trade and send it -> localy mark as Send
    # ------------------------------------------------------------------
    def get_send(self, strategy_id) -> Trade:  
        """ 
        Get last send trade
        Args:
            strategy_id(int): 
                ID of a strategy

        Returns:
            Trade:
                Trade structure to send.
        """
        try:
            with self._lock:
                time_old_seconds = self._get_settings("liveTradeAging")
                idx = strategy_id
                #Table should be setup but still check
                if idx not in self._data: 
                    return None
                if self._data[idx].paper: #If paper trading do nothing
                    return None
                trades = self._data[idx].trades
                send_idx = self._get_last(trades, "Send")        
                if send_idx is None:
                    return None   
                if not self._check_trade_age_ok(idx, send_idx,time_old_seconds): #Trade to old
                    return None 

                return copy.deepcopy(self._data[idx].trades[send_idx])
        except Exception as e:
            self._logger.error(f"TradeManager get_open() error: {e}")
    

    # Write in the table
    # ------------------------------------------------------------------
    def set_close(self,strategy_id,  trade: Trade) -> bool:   
        """ 
        Update data of "Send" trade after recived response from API
        Args:
            strategy_id(int): 
                ID of a strategy 
            trade(Trade):
                Updated trade status.

        Returns:
            bool:
                if succesful.
        """
        try:
            with self._lock:
                idx = strategy_id
                #Table should be setup but still check
                if idx not in self._data: 
                    return False
                if self._data[idx].paper: #If paper trading do nothing
                    return False
                trades = self._data[idx].trades
                edit_id_ = self._get_last(trades, "Send")
                if edit_id_ is None:
                    return False        
                self._data[idx].trades[edit_id_] = trade
                s1 = self._data[idx].symbol1
                s2 = self._data[idx].symbol2
                type_s = self._data[idx].type_s
                rows = self._trades_to_array(self._data[idx].trades)
                save_csv(build_trade_path(s1,s2,idx,type_s),rows)
                return True
        except Exception as e:
            self._logger.error(f"TradeManager set_close() error: {e}")
    
    # Get table
    # ------------------------------------------------------------------
    def get_table(self, strategy_id) -> list[Trade]: 
        """ 
        Args:
            strategy_id(int): 
                ID of a strategy 

        Returns:
            list[Trade]:
                Returns the whole trade table. None if empty
        """
        try:
            with self._lock:
                idx = strategy_id
                if idx not in self._data: 
                    return None
                if self._data[idx].paper:
                    return self._data[idx].paper_trades
                return copy.copy(self._data[idx].trades)
        except Exception as e:
            self._logger.error(f"TradeManager get_table() error: {e}")
    
    # Get last trade in table table
    # ------------------------------------------------------------------
    def get_last_trade(self, strategy_id) -> Trade: 
        """ 
        Args:
            strategy_id(int): 
                ID of a strategy 

        Returns:
            list[Trade]:
                Returns the whole trade table. None if empty
        """
        try:
            with self._lock:
                idx = strategy_id
                if idx not in self._data: 
                    return None
                if self._data[idx].paper:
                    return self._data[idx].paper_trades[-1]
                return copy.deepcopy(self._data[idx].trades[-1])
        except Exception as e:
            self._logger.error(f"TradeManager get_table() error: {e}")
    
    # Get first trade timestamp
    # ------------------------------------------------------------------
    def get_first_timestamp(self, strategy_id) -> int:
        """ 
        Args:
            strategy_id(int): 
                ID of a strategy 

        Returns:
            int:
                Returns timestamp in seconds of first trade or now()
        """
        try:
            idx = strategy_id
            if idx not in self._data:
                return self._now()
            
            if self._data[idx].paper:
                trades: list[Trade] = self._data[idx].paper_trades
            else:
                trades : list[Trade] = self._data[idx].trades
            if not trades :
                return self._now()
            
            return int(trades[0].timestamp / 1000)
        except Exception as e:
            self._logger.error(f"TradeManager get_first_timestamp() error: {e}")
    
    # Helpers
    # ==================================================================   
    # Return last trade filtered by idx 
    # ------------------------------------------------------------------
    def _get_last(self,trades, filter) -> int: #Tested 28.11.2025
        if not trades: #Check if data exists
            return None        
        reverse = trades[::-1]
        for idx, trade in enumerate(reverse):
            if trade.idx == filter:
                return -1-idx #revers table get trade index
    
    # Return first trade filtered by idx
    # ------------------------------------------------------------------
    def _get_first(self,trades, filter) -> int: 
        if not trades: #Check if data exists
            return None        
        for idx, trade in enumerate(trades):
            if not filter:
                return 0
            if trade.idx == filter:
                return idx #revers table get trade index
    
    # Remocve trades if they are to old for Open and Send (if not executed in time)
    # ------------------------------------------------------------------
    def _table_cleanup(self, strategy_id):
        idx = strategy_id
        time_old_seconds = self._get_settings("liveTradeAging")
        trades = self._data[idx].trades
        self._table_cleanup_idx(idx, time_old_seconds, trades, "Open")
        self._table_cleanup_idx(idx, time_old_seconds, trades, "Send")
    
    # Remove trade if it is to old filtered by idx
    # ------------------------------------------------------------------
    def _table_cleanup_idx(self, strategy_id, time_old_seconds, trades, idx): 
        first_id = self._get_first(trades, idx)
        if first_id is None:
            return
        if not self._check_trade_age_ok(strategy_id, first_id, time_old_seconds):
            del trades[first_id]

    # check the age of the trade True it is ok False to old 
    # ------------------------------------------------------------------
    def _check_trade_age_ok(self, strategy_id, trade_id, time_old_seconds) -> bool:
        now_seconds = self._now()
        trade_seconds = int(self._data[strategy_id].trades[trade_id].timestamp / 1000)
        compare_seconds = now_seconds - trade_seconds
        if time_old_seconds < compare_seconds: #Trade to old
            return False
        return True 
    #Initialize the table
    # ------------------------------------------------------------------
    def _set_table(self, strategy: StrategyConfig, reset: bool): 
        id_ = strategy.idx
        trades = []
        paper_trades = []

        if not reset and id_ in self._data:
            existing = self._data[id_]
            trades = existing.trades
            paper_trades = existing.paper_trades

        self._data[id_] = TradeTable(
            pair=f"{strategy.symbol1}{strategy.symbol2}",
            type_s=strategy.type_s,
            symbol1=strategy.symbol1,
            symbol2=strategy.symbol2,
            paper=strategy.asset_manager.paper_t,
            trades=trades,
            paper_trades=paper_trades,
        )
    # set all tables execute on start
    # ------------------------------------------------------------------
    def _load_all(self):        #Tested 28.11.2025
        strategies_ids = self._strategies_obj.get_id_list()

        for id_ in strategies_ids: #run trough list            
            strategy : StrategyConfig = self._strategies_obj.get_by_id(id_)
            id_ = strategy.idx
            s1 = strategy.symbol1
            s2 = strategy.symbol2
            type_s = strategy.type_s
            self._set_table(strategy, True)
            #Read data from files for Trades and paper trades
            trades_data = load_csv(build_trade_path(s1,s2,id_,type_s))
            self._data[id_].trades = self._array_to_trade(trades_data)            
            trades_data = load_csv(build_trade_path(s1,s2,id_,type_s,"Paper"))
            self._data[id_].paper_trades = self._array_to_trade(trades_data) 
    
    # ------------------------------------------------------------------
    @staticmethod
    def _now():        
        now_utc = datetime.now(timezone.utc)
        return int(now_utc.timestamp())       
    
    @staticmethod
    def _now_ms():        
        now_utc = datetime.now(timezone.utc)
        return int(now_utc.timestamp()*1000)    
    #Define data structure anf format recived array from csv
    @staticmethod
    def _array_to_trade(arr):
        if arr is None:
            return []        
        trades = []

        for row in arr:
            trades.append(
                Trade(
                    timestamp=int(row[TRADE_TABLE_COL_TIMESTAMP]),
                    idx=str(row[TRADE_TABLE_COL_ID]),
                    symbol1=str(row[TRADE_TABLE_COL_SYMBOL_1]),
                    quantity1=float(row[TRADE_TABLE_COL_ASSET_S1_QT]),
                    symbol2=str(row[TRADE_TABLE_COL_SYMBOL_2]),
                    quantity2=float(row[TRADE_TABLE_COL_ASSET_S2_QT]),
                    price=float(row[TRADE_TABLE_COL_PRICE]),
                    max_p=float(row[TRADE_TABLE_COL_MAX]),
                    min_p=float(row[TRADE_TABLE_COL_MIN]),
                    lookback=int(row[TRADE_TABLE_COL_LOOKBACK]),
                    avg_cost=float(row[TRADE_TABLE_COL_AVG_COST]),
                    change=float(row[TRADE_TABLE_COL_CHANGE]),
                    commision=float(row[TRADE_TABLE_COL_COMMISION]),
                    commision_symbol=str(row[TRADE_TABLE_COL_COMMISION_ASSET]),
                )
            )
        return trades

    @staticmethod
    def _trades_to_array(trades : list[Trade]):
        rows = []
        for t in trades:
            rows.append([
                t.timestamp,
                t.idx,
                t.symbol1,
                t.quantity1,
                t.symbol2,
                t.quantity2,
                t.price,
                t.max_p,
                t.min_p,
                t.lookback,
                t.avg_cost,
                t.change,
                t.commision,
                t.commision_symbol
            ])
        return rows
