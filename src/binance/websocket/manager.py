from .models import WebsocketCmd

from src.models import Trade, Balance
from src.utils.storage import load_json, save_json

import threading
from typing import Dict
import copy
import logging
import time
from datetime import datetime, timezone
import uuid

from binance_sdk_spot.websocket_api.models import (AccountStatusResponseResult, 
                                                   AccountStatusResponseResultBalancesInner, 
                                                   PingResponse,
                                                   KlinesIntervalEnum,
                                                   ExchangeInfoResponseResultSymbolsInner,
                                                   OrderPlaceResponseResult,
                                                   RateLimitsInner
)


# WebsocketManager Class (long-living)
# ---------------------------------------------------------------------- 
class WebsocketManager:
    """ 
        (long-living) Class for executing commands with websocket API. 
        Class sends commands to WebsocketConnection and recives responds.

    Managing exchange info data.        
    Thread-safe with a re-entrant lock.
    """  
    def __init__(self, 
                 path: str, 
                 lock: threading.Lock, 
                 event: threading.Event,
                 settings_get: callable,
                 ):    
        """ 
        Args:
            path(str):
                Path to the exchange info file .json
            lock(threading.Lock):
                Thread lock for connecting with WebsocketConnection.
            event(threading.Event):
                Thread event for connecting with WebsocketConnection.

            settings_get(callable(str)):
                Function for retrieving settings.
        """
        self._ws_cmds : WebsocketCmd = WebsocketCmd()
        self._settings_get = settings_get
        self._default_order_percision: int = 5
        self._path = path
        #threading
        self._comm_lock = lock
        self._comm_event = event
        self._internal_lock = threading.RLock()

        self._time_ping = self._now()
        self._exchange_info_data = {}
        self._last_ping_response: str = "None"
        self._timeout_ms : int = 10000
        
        # --- Logger Setup ---
        self._logger = logging.getLogger("binance").getChild(self.__class__.__name__)

    # Internal I/O storage 
    # ==================================================================
    # Load from exchange info .json
    # ---------------------------------------------------------
    def _load_exchange_info(self):
        self._exchange_info_data = load_json(self._path)

    # Save from self exchange to .json
    # ---------------------------------------------------------
    def _save_exchange_info(self):
        save_json(self._path, self._exchange_info_data)

    # Public 
    # ==================================================================
    # retur if connected
    # --------------------------------------------------------- 
    def is_connected(self) ->bool:
        """Returns:
            bool: 
                connection status
        """
        with self._internal_lock:
            return self._ws_cmds.connected

    # get exchange info
    # ---------------------------------------------------------  
    def get_exchange_info(self) -> dict:
        """
        Returns:
            dict:
                All existing data of exchange pairs.
        """
        with self._internal_lock:
            return copy.copy(self._exchange_info_data)
    
    # check if pair is tradeing on exchange
    # ---------------------------------------------------------  
    def check_pair_exist(self, pair) -> bool:
        """
        Args:
            pair(str):
                Symbol pair to check
        Returns:
            bool:
        """        
        with self._internal_lock:
            if pair in self._exchange_info_data:
                return True
            return False

    # check if pair is tradeing on exchange
    # ---------------------------------------------------------  
    def get_pair_order_precision(self, pair) -> int:
        """
        Args:
            pair(str):
                Symbol pair to check
        Returns:
            int:
                Number of decimal places to round the order to.
        """
        with self._internal_lock:
            if self.check_pair_exist(pair):
                return int(self._exchange_info_data[pair]["order_precision"])
            return int(self._default_order_percision) #Default        

    # get last ping response
    # ---------------------------------------------------------  
    def get_last_ping_resp(self) -> str:
        """
        Pings server if time passed or returns last ping data.
        Returns:
            PingResponse:
                Data of last ping response
        """        
        with self._internal_lock:
            now_seconds = self._now()
            time_passed = now_seconds - self._time_ping
            ping_response = copy.deepcopy(self._last_ping_response)

            should_ping = (
                time_passed > int(self._settings_get("pingUpdate") * 60)
                or not ping_response
            )

            if should_ping:
                self._time_ping = now_seconds

        if should_ping:
            self.ping_ws()
        
        with self._internal_lock:
            return copy.deepcopy(self._last_ping_response)

    # Connection commands 
    # ==================================================================
    #Disconnect both by sending cmd to the threads
    def disconnect(self):
        """
        Sends a disconnect command to API connection.
        """
        print("Disconnecting Websocket from API")
        with self._comm_lock: #Locking the change to websocet_cmds
            self._ws_cmds.cmd = "disconnect"            
            self._ws_cmds.diconnect = True  

    # ping server
    # ---------------------------------------------------------  
    def ping_ws(self) -> PingResponse:
        """
        Sends a ping command  to API connection.
        Returns:
            PingResponse:
                Ping data response of error string.
        """
        try:            
            with self._internal_lock:
                if not self._ws_cmds.connected: #Check for connection
                    raise ConnectionError("No connection to WebSocket")
                 
            self._wait_for_done()

            with self._comm_lock: #Lock to send cmds
                rand_uuid = uuid.uuid4()
                self._ws_cmds.id = rand_uuid
                self._ws_cmds.cmd = "ping"

            #wait for the communication module locks since Comm module is in another thread this can wait with stoping current thread
            if not self._comm_event.wait(timeout=int(self._timeout_ms /1000 *2)):
                raise TimeoutError("Timeout waiting event from websocket thread")

            with self._comm_lock: #wait for result   
                if rand_uuid != self._ws_cmds.respons_id:
                    self._logger.error(f"ping_ws() error: uuid mismatch send= {rand_uuid} response= {self._ws_cmds.respons_id}")  

                self._logger.debug(f"ping_ws() return: {self._ws_cmds.respons_data}")
                formated_resp = self._format_ping_response(self._ws_cmds.respons_data, self._now())
                
            with self._internal_lock:
                self._last_ping_response = formated_resp
                return self._last_ping_response
        except Exception as e:
            self._logger.error(f"ping_ws() error: {e} id={self._ws_cmds.id}")
            return f"ping_ws() error: {e} id={self._ws_cmds.id}"
        
        finally:
            with self._comm_lock: 
                self._ws_cmds.id = ""   

    # #Geting user data balances
    # ---------------------------------------------------------    
    def fetch_user_data(self) -> dict[str , Balance]:
        """
        Sends a user data command  to API connection.
        Returns:
            dict[key : Balance]:
                Dictionary of all symbols and thair non zero balances.
        """
        
        try:
            with self._internal_lock:
                if not self._ws_cmds.connected: #Check for connection
                    raise ConnectionError("No connection to WebSocket")
                
            self._wait_for_done()
            
            with self._comm_lock: #Lock to send cmds
                rand_uuid = uuid.uuid4()
                self._ws_cmds.id = rand_uuid
                self._ws_cmds.cmd = "user_data"
                
            #wait for the communication module 
            if not self._comm_event.wait(timeout=int(self._timeout_ms /1000 *2)):
                raise TimeoutError("Timeout waiting event from websocket thread")
            
            with self._comm_lock: #wait for result                
                if rand_uuid != self._ws_cmds.respons_id:
                    self._logger.error(f"fetch_user_data() error: uuid mismatch send= {rand_uuid} response= {self._ws_cmds.respons_id}") 
                
                data : AccountStatusResponseResult = copy.deepcopy(self._ws_cmds.respons_data) # copy data       
            
            with self._internal_lock:
                balances = data.balances
                return self._format_user_response(balances)  

        except Exception as e:
            self._logger.error(f"fetch_user_data() error: {e} id={self._ws_cmds.id} \n response -> {self._ws_cmds.respons_data}")
            return None
        
        finally:
            with self._comm_lock: 
                self._ws_cmds.id = ""   
        
    #Geting exchange info if not in .json can be forced
    # ---------------------------------------------------------  
    def fetch_exchange_info(self, force=False) -> dict: #only fetch onece in lifetime then save to json
        """
        Sends a exchange info command  to API connection.
        Args:
            force(bool):
                If true command will be send.
                If false the command will be send only if file does not exist.
        Returns:
            dict:
            All existing data of exchange pairs.
        """        
        try:               
            with self._internal_lock:     
                if not self._ws_cmds.connected: #Check for connection
                    raise ConnectionError("No connection to WebSocket")
            
            with self._internal_lock:    
                self._load_exchange_info()
                if self._exchange_info_data and not force:
                    return self._exchange_info_data
                
            self._wait_for_done()

            with self._comm_lock: #Lock to send cmds
                rand_uuid = uuid.uuid4()
                self._ws_cmds.id = rand_uuid
                self._ws_cmds.cmd = "exchange_info"

            #wait for the communication
            if not self._comm_event.wait(timeout=int(self._timeout_ms /1000 *10)):
                raise TimeoutError("Timeout waiting event from websocket thread")
            
            with self._comm_lock: #wait for result                
                if rand_uuid != self._ws_cmds.respons_id:
                    self._logger.error(f"fetch_exchange_info() error: uuid mismatch send= {rand_uuid} response= {self._ws_cmds.respons_id}")  

                resp = self._ws_cmds.respons_data
                if not resp:
                    return None                
                self._exchange_info_data = self._format_exchange_info_response(resp) # copy data       

            with self._internal_lock:    
                self._save_exchange_info()
                return self._exchange_info_data
            
        except Exception as e:
            self._logger.error(f"fetch_exchange_info() error: {e} id={self._ws_cmds.id}")
            return self._exchange_info_data
        
        finally:
            with self._comm_lock: 
                self._ws_cmds.id = ""   

    #fetch historic data and store in csv
    # ---------------------------------------------------------  
    def fetch_kline(self, symbol1, symbol2, interval, num_data:int = 100) -> list[dict]:    
        """
        Sends a fetch kline command  to API connection.
        Args:
            symbol1(str):
                Symbol of an asset.
            symbol2(str):
                Symbol of an asset.
            interval(str):
                Interval of the kLine example "1d"
            num_data(int, optional):
                Number of candles to retrive.
        Returns:
            list[dict]:
                kLine data list.
        """        
        try:
            with self._internal_lock:    
                if not self._ws_cmds.connected: #Check for connection
                    raise ConnectionError("No connection to WebSocket")
                
            self._wait_for_done()

            with self._comm_lock: #Lock to send cmds
                rand_uuid = uuid.uuid4()
                self._ws_cmds.id = rand_uuid
                self._ws_cmds.cmd_data = {
                    "symbol" : f"{symbol1}{symbol2}",
                    "interval" : KlinesIntervalEnum[f"INTERVAL_{interval}"].value,
                    "limit" : num_data
                }
                self._ws_cmds.cmd = "history"

            #wait for the communication module  
            if not self._comm_event.wait(timeout=int(self._timeout_ms /1000 *4)):
                raise TimeoutError("Timeout waiting event from websocket thread")
            
            with self._comm_lock: #wait for result                       
                if rand_uuid != self._ws_cmds.respons_id:
                    self._logger.error(f"fetch_kline() error: uuid mismatch send= {rand_uuid} response= {self._ws_cmds.respons_id}")  

                kline_data = copy.deepcopy(self._ws_cmds.respons_data) # copy data 
                
                if "error" in kline_data:
                    raise ValueError(kline_data)
                
            with self._internal_lock:   
                self._logger.info(f"fetch_kline() for {symbol1}/{symbol2} {interval} updated")
                return kline_data
        except Exception as e:
            self._logger.error(f"fetch_kline() error: {e} id={self._ws_cmds.id}")
            return None
        
        finally:
            with self._comm_lock: 
                self._ws_cmds.id = ""   

    #send Trade to binance
    # ---------------------------------------------------------  
    def send_trade(self, open_trade: Trade) -> Trade:
        """
        Sends a MARKET trade command  to API connection.
        Args:
            open_trade(Trade):
                Trade to send.
        Returns:
            Trade:
                updated trade with response from API.
        """  
        
        try: 
            with self._internal_lock:   
                if not self._ws_cmds.connected: #Check for connection
                    raise ConnectionError("No connection to WebSocket")   
                
                websocet_msg = self._format_order_place_msg(open_trade)

            self._wait_for_done()

            with self._comm_lock: #Lock to send command and data                
                rand_uuid = uuid.uuid4()

                self._ws_cmds.id = rand_uuid
                self._ws_cmds.cmd_data = websocet_msg
                self._ws_cmds.cmd = "trade"
                self._logger.info(f"send_trade() send order: {self._ws_cmds.cmd_data}")

            #wait for the communication module locks since     
            if not self._comm_event.wait(timeout=int(self._timeout_ms /1000 *3)):
                raise TimeoutError("Timeout waiting event from websocket thread")
            
            with self._comm_lock:                    
                if rand_uuid != self._ws_cmds.respons_id:
                    self._logger.error(f"send_trade() error: uuid mismatch send= {rand_uuid} response= {self._ws_cmds.respons_id}")                  

                tradeData = copy.deepcopy(self._ws_cmds.respons_data) # copy data
            
            with self._internal_lock:  
                response_result: OrderPlaceResponseResult = tradeData.result 
                self._logger.info(f"send_trade() recive order data: {response_result}")
                if response_result.status == "FILLED": #If filled update and return the trade order 
                    trade_closed = self._format_order_response_data(response_result, open_trade)
                    return trade_closed

        except Exception as e:
            self._logger.error(f"send_trade() error: {e} id={self._ws_cmds.id}")
            return None
        
        finally:
            with self._comm_lock: 
                self._ws_cmds.id = ""   

    # Helpers
    # ==================================================================
    #prepare data to Send TRADE to API
    # ---------------------------------------------------------
    def _format_order_place_msg(self, trade:Trade):
        pair =  f"{trade.symbol1}{trade.symbol2}" #Get trading simbols row 2 and row 4                        
        round_order = self.get_pair_order_precision(pair)

        if float(trade.quantity1) < 0.0:
            side="SELL"
            quote_order_qty= 0
            quantity = round(abs(float(trade.quantity1)), round_order) #When selling I want to sell the amount of Symbol1 I will recive Symbol2 depending on the market                        
        else:
            side="BUY"
            quote_order_qty= round(abs(float(trade.quantity2)), round_order)#When buying spend amount of symbol2 and recive amount of symbol1 depending on market
            quantity= 0        
        websocet_msg = {
                    "side" : side,
                    "symbol" : pair,
                    "quote_order_qty" : quote_order_qty,
                    "quantity" : quantity,
                    "symbol1" : trade.symbol1,
                    "symbol2" : trade.symbol2,
                }
        return websocet_msg
    
    # Waiting for done cmd befor sending new cmd.
    def _wait_for_done(self) -> bool:
        start = self._now_ms()
        timeout = self._timeout_ms + start
        done = False
        while not done:
            with self._comm_lock:
                if self._ws_cmds.cmd == "done" and self._ws_cmds.id == "":
                    done = True

            if self._now_ms() > timeout:
                with self._comm_lock:
                     self._ws_cmds.id = ""
                msg = f"WebSocketManager timeout {self._timeout_ms} ms waiting for (done) from WebsocketConnection"
                print(msg)
                raise TimeoutError(msg)
            time.sleep(0.2)

    # Utilities
    # ==================================================================
    @staticmethod
    def _now() -> int:
        return int(datetime.now(timezone.utc).timestamp())
    @staticmethod
    def _now_ms() -> int:
        return int(datetime.now(timezone.utc).timestamp()*1000)
    
    #Format trade data after reciving response "FILLED"
    # ---------------------------------------------------------
    @staticmethod
    def _format_ping_response(response_result : PingResponse, time_now) ->str:  
        text = ""
        if isinstance(response_result,PingResponse):
            if "error" in response_result:
                text = response_result
            else:
                rate_limits :RateLimitsInner = response_result.rate_limits[0]
                text = (f"id= {response_result.id}"
                        f"\n Update time {datetime.fromtimestamp(time_now)}"
                        f"\n Rate Limits:"
                        f"\n  Interval= {rate_limits.interval} num= {rate_limits.interval_num},"
                        f"\n  Limits= {rate_limits.count} / {rate_limits.limit}")
        return text 

    #Format trade data after reciving response "FILLED"
    # ---------------------------------------------------------
    @staticmethod
    def _format_order_response_data(response_result : OrderPlaceResponseResult, open_trade: Trade) ->Trade:    
        trade:Trade = copy.copy(open_trade)
        trade.timestamp = response_result.transact_time
        trade.idx = response_result.client_order_id
        if float(trade.quantity1) > 0.0: #if buy then write positive values
            trade.quantity1 = float(response_result.executed_qty)
            trade.quantity2 = -float(response_result.cummulative_quote_qty)
        else:
            trade.quantity1 = -float(response_result.executed_qty)
            trade.quantity2 = float(response_result.cummulative_quote_qty)
        price = round(float(response_result.cummulative_quote_qty)/  float(response_result.executed_qty), 8)                                                     
        commission = 0.0
        commission_asset = "BNB"
        for part in response_result.fills: #go trough filled data for commision calculation 
            commission += float(part.commission)
            commission_asset = part.commission_asset   
        trade.price = price #Calculated price maybe we can calculated out of every fill but dont think it is necesary
        trade.commision = commission
        trade.commision_symbol = commission_asset        
                                    
        return trade
    
    # Format user data recived
    # ---------------------------------------------------------
    @staticmethod
    def _format_user_response(balances: list[AccountStatusResponseResultBalancesInner]) -> dict[str : Balance]:
        if not balances:
            return None
        balance_dict = {}
        for balance in balances:
            balance_dict[balance.asset]= Balance(
                                available= float(balance.free),
                                locked= float(balance.locked),
                                total= float(balance.free) + float(balance.locked))
            
        return balance_dict
    
    # Format exchange_info data recived
    # ---------------------------------------------------------
    @staticmethod
    def _format_exchange_info_response(resp: list[ExchangeInfoResponseResultSymbolsInner]):
        resp_list = {}
        for obj in resp:
            resp_list[obj.symbol]={}
            resp_list[obj.symbol]["base_asset_precision"] = obj.base_asset_precision
            resp_list[obj.symbol]["quote_asset_precision"] = obj.quote_asset_precision
            resp_list[obj.symbol]["quote_precision"] = obj.quote_precision
            for filter in obj.filters:
                if filter.filter_type == 'LOT_SIZE':
                    resp_list[obj.symbol]["step_size"] = float(filter.step_size)
                    resp_list[obj.symbol]["min_qty"] = float(filter.min_qty)
                    resp_list[obj.symbol]["max_qty"] = float(filter.max_qty)
                    temp = float(filter.step_size)
                    order_precision =0
                    while temp < 1.0 and temp !=0:
                        temp *= 10
                        order_precision +=1
                    resp_list[obj.symbol]["order_precision"] = order_precision
        return resp_list
        
    


