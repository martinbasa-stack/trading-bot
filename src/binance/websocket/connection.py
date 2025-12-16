from src.telegram import send_telegram_msg
from .models import WebsocketCmd

import asyncio
import os
import threading
import logging
import time

from binance_sdk_spot.spot import (
    Spot,
    ConfigurationWebSocketAPI,
    SpotWebSocketAPI
    )
from binance_common.constants import WebsocketMode
from binance_sdk_spot.websocket_api.models import ExchangeInfoSymbolStatusEnum



# WebsocketConnection Class (separate thread)
# ======================================================================
class WebsocketConnection:
    """ 
        Class for establishning and maintaining API connection. Dependant on WebsocketManager Class
   
    Thread-safe with lock.
    """  
    def __init__(self,
                 lock: threading.Lock, 
                 event: threading.Event, 
                 ws_cmds : WebsocketCmd, 
                 settings_get: callable):          
        """ 
        Args:
            lock(threading.Lock):
                Thread lock for connecting with WebsocketManager.
            event(threading.Event):
                Thread event for connecting with WebsocketManager.
            ws_cmds(WebsocketCmd):
                Commands and responsed dataClass for connecting with WebsocketManager.

            settings_get(callable(str)):
                Function for retrieving settings.
        """
        self.ws_cmds : WebsocketCmd = ws_cmds
        self._api_key = ""
        self._api_secret = ""
        self._settings_get = settings_get
        self._backoff_attempt = 0
        self._get_api()  

        self._error_count: int = 0

        #threading
        self._comm_lock = lock
        self._comm_event = event

        # --- Logger Setup ---
        self._logger = logging.getLogger("binance").getChild(self.__class__.__name__)
    
    # Public only 1!
    # ==================================================================
    # Run the loop and manage reconnection
    # ---------------------------------------------------------  
    def run(self):
        """Run while loop that will only close on disconnect."""
        backoff_base = 1.5
        reconnectPause = 45

        disconnect = False

        while not disconnect:            
            self._error_count = 0
            #self._create_async_loop()
            asyncio.run(self._connection_loop())

            with self._comm_lock:
                disconnect = self.ws_cmds.diconnect    
            
            if not disconnect: #if shud down event is set no need to sleep
                # Backoff before attempting a clean fresh reconnect
                self._backoff_attempt += 1
                sleep_time = min(reconnectPause * (backoff_base ** (self._backoff_attempt - 1)), 300)
                msg = f"WebsocketConnection() stopped unexpectedly - restarting after {sleep_time} s"
                self._logger.error(msg) 
                print(msg) 
                time.sleep(sleep_time) 

    # Helpers
    # ==================================================================
    # connection loop here
    # ---------------------------------------------------------  
    async def _connection_loop(self):      
        self._logger.info("WebsocketConnection() Starts the event loop")    
        connection = None    
        configuration_ws_api = self._config()
        
        try:   
            self._comm_event.clear()
            # Initialize Spot client
            client = Spot(config_ws_api=configuration_ws_api)
            # Establish connection to API
            if connection == None:
                connection = await client.websocket_api.create_connection() # connect to binance

            self._backoff_attempt = 0
            self._error_count=0  

            self._logger.info("Connected")      

            await asyncio.sleep(2)

            disconnect = False 
            while not disconnect:    

                with self._comm_lock:
                    self.ws_cmds.connected = True  
                    disconnect = self.ws_cmds.diconnect  


                self._comm_event.clear()
                await asyncio.sleep(self._settings_get("websocetManageLoopRuntime"))

                with self._comm_lock:
                    disconnect = self.ws_cmds.diconnect

                if self.ws_cmds.cmd != "done":
                    with self._comm_lock: #Locking the change to websocet_cmds
                        self.ws_cmds.respons_data = None #write return in case no data
                        self.ws_cmds.respons_id = ""
                        match self.ws_cmds.cmd: #Sending requests to API
                            case "disconnect": 
                                self.ws_cmds.diconnect = True
                                break
                            case "exchange_info":
                               await self._exchange_info(connection)
                            case "ping": #Ping client    
                                await self._ping(connection)                
                            case "history": #Retrive kLine history
                                await self._kline_hist(connection)
                            case "trade":
                                await self._trade(connection)                                                      
                            case "user_data":
                                await self._user_data(connection)
                        
                        if self.ws_cmds.cmd !="ping":
                            self._logger.info(f"Command executed -> {self.ws_cmds.cmd} <- ")
                        self.ws_cmds.respons_id = self.ws_cmds.id
                        self.ws_cmds.cmd = "done"       
                                                    
                    self._comm_event.set()
                    
                #await asyncio.sleep(0.01)

                if self._error_count > 2: #if errors excede X start reconnect
                    self._logger.error(f"Connection error count: {self._error_count} -> Reconnect")
                    with self._comm_lock:
                        self.ws_cmds.cmd = "error"       
                        self.ws_cmds.respons_data = "error"
                    self._error_count = 0
                    break #Disconnect

        except Exception as e:  
            with self._comm_lock:
                self.ws_cmds.connected = False    
                self.ws_cmds.cmd = "error"       
                self.ws_cmds.respons_data = "error"
            msg = f"WebsocketConnection fatal error: {e}"
            self._logger.error(msg)
            print(msg) 
            send_telegram_msg(msg)
        finally:     
            with self._comm_lock:
                self.ws_cmds.connected = False    
            self._comm_event.set() #release functions if they are waiting for event
            await asyncio.sleep(0.05) 
            self._comm_event.clear() #Block after released for response 

            await self._cleanup(connection, client)
            connection = None
            client = None

    # Communication helper
    # ==================================================================
    # Fetch exchange info
    # -----------------------------------------------------------------
    async def _exchange_info(self, connection : SpotWebSocketAPI): 
        try:
            response = await connection.exchange_info(#symbols= ["BTCUSDC", "ETHUSDC", "DSEFS"],
                permissions="SPOT",
                symbol_status = ExchangeInfoSymbolStatusEnum.TRADING,
                show_permission_sets=False
                )
            responseBigData = response.data().result.symbols
            self.ws_cmds.respons_data = responseBigData
            self._logger.info(f"exchange_info() asset list recived")
        except Exception as e:
            self._logger.error(f"Connection error: exchange_info() {e}")
            self.ws_cmds.respons_data = "error"
            self._error_count +=1  
            print(f"Connection error count: {self._error_count}")

    # Ping
    # -----------------------------------------------------------------
    async def _ping(self, connection : SpotWebSocketAPI): 
        try:                    
            response = await connection.ping()
            rate_limits = response.rate_limits
            responseData = response.data()
            self._logger.debug(f"ping() rate limits: {rate_limits}")    
            self.ws_cmds.respons_data = responseData
        except Exception as e:
            self._logger.error(f"WebsocketConnection() Connection error: ping() {e}")
            self.ws_cmds.respons_data = "error"
            self._error_count +=1      
            print(f"Connection error count: {self._error_count}")
    
    # User Data
    # -----------------------------------------------------------------
    async def _user_data(self, connection : SpotWebSocketAPI): 
        try:
            response = await connection.account_status(omit_zero_balances=True)                     
            responseData = response.data().result
            self.ws_cmds.respons_data = responseData
        except Exception as e:
            self._logger.error(f"Connection error: account_status() {e}")
            self.ws_cmds.respons_data = "error"
            self._error_count +=1     
            print(f"Connection error count: {self._error_count}")

    
    # kLine history
    # -----------------------------------------------------------------
    async def _kline_hist(self, connection : SpotWebSocketAPI):
        try:
            response = await connection.klines(
                symbol= self.ws_cmds.cmd_data["symbol"],
                interval= self.ws_cmds.cmd_data["interval"],
                limit= self.ws_cmds.cmd_data["limit"]
            )                                      
            responseData = response.data().result # open only results from the data                           
            self.ws_cmds.respons_data = responseData
        except Exception as e:
            self._logger.error(f"Connection error: klines() {e}")
            self.ws_cmds.respons_data = "error"
            self._error_count +=1   
            print(f"WebsocketConnection() Connection error count: {self._error_count}")

    # Send trade
    # -----------------------------------------------------------------
    async def _trade(self, connection : SpotWebSocketAPI):
        try:                                    
            if self.ws_cmds.cmd_data["quantity"] > 0:
                print(f"SELL order send {self.ws_cmds.cmd_data}")
                response = await connection.order_place(
                    symbol= self.ws_cmds.cmd_data["symbol"],
                    side= self.ws_cmds.cmd_data["side"],
                    type= "MARKET",
                    quantity = self.ws_cmds.cmd_data["quantity"],   #amount of Symbol 1 want to Sell 
                )    
            else:
                print(f"BUY order send {self.ws_cmds.cmd_data}")
                response = await connection.order_place(
                    symbol= self.ws_cmds.cmd_data["symbol"],
                    side= self.ws_cmds.cmd_data["side"],
                    type= "MARKET",
                    quote_order_qty= self.ws_cmds.cmd_data["quote_order_qty"] #quoted is the number of Symbol2 you want to spend or get
                )                            
            responseData = response.data()
            self.ws_cmds.respons_data = responseData
            self._logger.info(f"Order posted succesfuly on {responseData.result.symbol} "
                        f"with id = {responseData.result.client_order_id} | status = {responseData.result.status}")     
        except Exception as e:                                
            self._logger.error(f"Connection error: order_place() {e}")
            self.ws_cmds.respons_data = "error"   
            self._error_count +=1    
            print(f"Connection error count: {self._error_count}")

    # Cleanup
    # ==================================================================
    async def _cleanup(
        self,
        connection: SpotWebSocketAPI | None,
        client: Spot | None
    ):
        self._logger.warning("Starting websocket cleanup")

        # ---- 1. STOP NEW COMMANDS IMMEDIATELY ----
        with self._comm_lock:
            self.ws_cmds.connected = False  # <-- your guards rely on this

        # ---- 2. CLOSE WEBSOCKET CONNECTION ----
        if connection:
            try:
                retries  = 0
                while connection.connections and retries < 10:
                    self._logger.warning(f"Closing connection {connection}")
                    await connection.close_connection(close_session=True)
                    await asyncio.sleep(0.5)
                    retries +=1
                    
                self._logger.warning("WebSocket connection closed")
            except asyncio.TimeoutError:
                self._logger.error("WebSocket close timed out")
            except Exception as e:
                self._logger.error(f"WebSocket close error: {e}")

        # ---- 3. CLOSE CLIENT SESSION ----
        if client:
            try:
                if hasattr(client, "session"):
                    await client.session.close()
                    self._logger.warning("HTTP session closed")
                    
            except Exception as e:
                self._logger.error(f"Client close error: {e}")

        # ---- 4. CANCEL ONLY TASKS OWNED BY THIS OBJECT ----
        tasks = [
            t for t in asyncio.all_tasks()
            if t is not asyncio.current_task()
            and getattr(t, "_owner", None) is self
        ]        
        if tasks:
            self._logger.warning(f"Cancelling {len(tasks)} owned tasks")
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

        self._logger.info("Cleanup complete")
        self._logger.info(f"After cleanup: connection: {connection} | client: {client}")
        print("WebsocketConnection cleanup complete")

    # Create configuration for the WebSocket API
    # ---------------------------------------------------------  
    def _config(self) -> ConfigurationWebSocketAPI:
        configuration_ws_api = ConfigurationWebSocketAPI(
            api_key = self._api_key,
            api_secret = self._api_secret,
            timeout= self._settings_get("timeout"),
            reconnect_delay= self._settings_get("reconnect_delay"),
            mode= WebsocketMode.SINGLE,
            pool_size=1
            )
        self._logger.info(f"WebsocketConnection() connection configuration: \n timeout={configuration_ws_api.timeout},"
                    f" reconnect_delay={configuration_ws_api.reconnect_delay}, "
                    f" stream_url={configuration_ws_api.stream_url}, "
                    f" unit={configuration_ws_api.time_unit}, "
                    f" mode={configuration_ws_api.mode}, "
                    f" pool_size={configuration_ws_api.pool_size}, "
                    f" https_agent={configuration_ws_api.https_agent}, "
                    )
        return configuration_ws_api

    #Get Binance API key and secret from file or enviroment
    # ---------------------------------------------------------  
    def _get_api(self):
        try:
            #Get keys from inviroment if not defined
            self._api_key = self._settings_get("API_KEY")
            self._api_secret = self._settings_get("API_SECRET")
            if "API_KEY" in self._api_key:
                self._api_key = os.environ.get("BINANCE_API_KEY")
            if "API_SECRET" in self._api_secret:
                self._api_secret = os.environ.get("BINANCE_API_SECRET")

        except Exception as e:
            self._logger.error(f"getAPI() error: {e}")
