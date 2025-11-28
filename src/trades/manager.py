from .models import Trade, TradeTable
from .storage import load_csv, save_csv, build_trade_path, delete_csv
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

# TradeManager Class
# ----------------------------------------------------------------------
class TradeManager:
    def __init__(self, get_strategy_by_id_func, get_strategies_ids_func):
        # get_pairs_intervals is a function get_pairs_intervals() from another class
        self.get_strategy_by_id = get_strategy_by_id_func
        self.get_strategies_ids = get_strategies_ids_func
        self.data: Dict[int, TradeTable] = {}  # TradeTables
        #At initialisation load all data 
        self._load_all()
    
    # Public 
    # ==================================================================
    #Update add new trade
    # ------------------------------------------------------------------
    def new_trade(self, strategy_id: int, trade :Trade):  #Tested 28.11.2025
        id_ = strategy_id
        strategy = self.get_strategy_by_id(id_)
        s1 = strategy["Symbol1"]
        s2 = strategy["Symbol2"]
        type_s = strategy["type"]
        #Build table if it does not exist
        if id_ not in self.data:            
            self._set_table(strategy, True)
        #Save data localy
        if self.data[id_].paper:
            self.data[id_].paper_trades.append(trade)
            path = build_trade_path(s1,s2,id_,type_s,"Paper")
            trades = self.data[id_].paper_trades
        else:
            self.data[id_].trades.append(trade)
            path = build_trade_path(s1,s2,id_,type_s)
            trades = self.data[id_].trades
        rows = self._trades_to_array(trades)
        #Save data to file
        save_csv(path,rows)
        
    #Cleanup -> delete local data if no strategy
    # ------------------------------------------------------------------
    def cleanup(self):
        strategies_ids = self.get_strategies_ids()
        for id_ in list(self.data): #run trough list            
            if id_ not in strategies_ids:
                self.delete(id_, True)

    #Delete trading tables of strategy and local data optional
    # ------------------------------------------------------------------
    def delete(self, strategy_id: int, local=False): #Tested 28.11.2025
        id_ = strategy_id
        if id_ not in self.data: #If there is no table already 
            return
        s1 = self.data[id_].symbol1
        s2 = self.data[id_].symbol2
        type_s = self.data[id_].type_s
        #Remove local data if selected
        if local: del self.data[id_]
        paths = [build_trade_path(s1,s2,id_,type_s,"Paper"),
                    build_trade_path(s1,s2,id_,type_s,)]
        delete_csv(paths) #remove files

    #Update datafrom strategy if strategy changed
    # ------------------------------------------------------------------
    def update(self, strategy_id:int):   #Tested 28.11.2025
        strategy = self.get_strategy_by_id(strategy_id)
        if strategy is None:
            return
        id_ = strategy["id"]
        if id_ not in self.data: #Create new
            self._set_table(strategy, True)
            return
        s1 = strategy["Symbol1"]
        s2 = strategy["Symbol2"]
        pair = f"{s1}{s2}"
        if pair != self.data[id_].pair:
            self.delete(id_)#Delete tables if new pair
            self._set_table(strategy, True)#Inserting new table will clear trades
        else:
            self._set_table(strategy, False)

    #Find last open trade and send it -> localy mark as Send
    # ------------------------------------------------------------------
    def get_open(self, strategy_id, time_old_seconds) -> Trade: #Tested 28.11.2025
        now_seconds = self._now()
        id_ = strategy_id
        #Table should be setup but still check
        if id_ not in self.data: 
            return None
        if self.data[id_].paper: #If paper trading do nothing
            return None
        trades = self.data[id_].trades
        open_id_ = self._get_last(trades, "Open")        
        if open_id_ is None:
            return None   
        #Check if it is old
        trade_seconds = int(self.data[id_].trades[open_id_].timestamp / 1000)
        compare_seconds = now_seconds - trade_seconds
        if time_old_seconds < compare_seconds: #Trade to old
            return None 
        #Write send to idx to mark it   
        self.data[id_].trades[open_id_].idx = "Send"

        return copy.deepcopy(self.data[id_].trades[open_id_])
    
    #Write in the table
    # ------------------------------------------------------------------
    def set_close(self,strategy_id,  trade: Trade) -> bool: #Tested 28.11.2025
        id_ = strategy_id
        #Table should be setup but still check
        if id_ not in self.data: 
            return False
        if self.data[id_].paper: #If paper trading do nothing
            return False
        trades = self.data[id_].trades
        edit_id_ = self._get_last(trades, "Send")
        if edit_id_ is None:
            return False        
        self.data[id_].trades[edit_id_] = trade
        s1 = self.data[id_].symbol1
        s2 = self.data[id_].symbol2
        type_s = self.data[id_].type_s
        rows = self._trades_to_array(self.data[id_].trades)
        save_csv(build_trade_path(s1,s2,id_,type_s),rows)
        return True
    
    #Get table
    # ------------------------------------------------------------------
    def get_table(self, strategy_id) -> list[Trade]:  #Tested 28.11.2025
        id_ = strategy_id
        if id_ not in self.data: 
            return None
        if self.data[id_].paper:
            return self.data[id_].paper_trades
        return copy.deepcopy(self.data[id_].trades)
    # Helpers
    # ==================================================================
     
    #Return last trade wher idx is specified
    # ------------------------------------------------------------------
    def _get_last(self,trades, filter) -> int: #Tested 28.11.2025
        if trades is None: #Check if data exists
            return None        
        reverse = trades[::-1]
        for idx, trade in enumerate(reverse):
            if trade.idx == filter:
                return -1-idx #revers table get trade index
    
    #Initialize the table
    # ------------------------------------------------------------------
    def _set_table(self, strategy: dict, reset: bool): #Tested 28.11.2025
        id_ = strategy["id"]
        trades = []
        paper_trades = []

        if not reset and id_ in self.data:
            existing = self.data[id_]
            trades = existing.trades
            paper_trades = existing.paper_trades

        self.data[id_] = TradeTable(
            pair=f"{strategy['Symbol1']}{strategy['Symbol2']}",
            type_s=strategy["type"],
            symbol1=strategy["Symbol1"],
            symbol2=strategy["Symbol2"],
            paper=strategy["paperTrading"],
            trades=trades,
            paper_trades=paper_trades,
        )
    # set all tables execute on start
    # ------------------------------------------------------------------
    def _load_all(self):        #Tested 28.11.2025
        strategies_ids = self.get_strategies_ids()

        for id_ in strategies_ids: #run trough list            
            strategy = self.get_strategy_by_id(id_)
            id_ = strategy["id"]
            s1 = strategy["Symbol1"]
            s2 = strategy["Symbol2"]
            type_s = strategy["type"]
            self._set_table(strategy, True)
            #Read data from files for Trades and paper trades
            trades_data = load_csv(build_trade_path(s1,s2,id_,type_s))
            self.data[id_].trades = self._array_to_trade(trades_data)            
            trades_data = load_csv(build_trade_path(s1,s2,id_,type_s,"Paper"))
            self.data[id_].paper_trades = self._array_to_trade(trades_data) 
    
    # ------------------------------------------------------------------
    @staticmethod
    def _now():        
        now_utc = datetime.now(timezone.utc)
        return int(now_utc.timestamp())        
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
    def _trades_to_array(trades):
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
