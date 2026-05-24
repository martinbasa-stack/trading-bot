from src.constants import INTERVAL_LIST
from .models import StreamKline
from .manager import StreamManager

import logging
import asyncio
import os
import threading
import time
from datetime import datetime, timezone
from typing import Dict
import uuid

from binance_sdk_spot.spot import (
    Spot,
    SPOT_WS_STREAMS_PROD_URL,
    ConfigurationWebSocketStreams,
    SpotWebSocketStreams
)
from binance_common.constants import WebsocketMode
from binance_sdk_spot.websocket_streams.models import KlineIntervalEnum

from binance_common.websocket import global_stream_connections #To solve reconnection problems delete stream for this list

# ======================================================================
# StreamWorker Class (separate thread)
# ======================================================================
class StreamWorker:
    """
    Stream connection and reconnection managment.
    """

    def __init__(
        self,
        stream_manager : StreamManager,
        get_pairs : callable,
        get_settings : callable,
        lock: threading.Lock,
        max_no_data: int = 5
    ):
        """
        Args:
            stream_manager˙(StreamManager): 
                Manager class.

            get_pairs(callable(filter_only = None, filter_exclude = None)): 
                Function to retrive pairs from Strategymanager.

            get_settings(callable(str)):
                Function to get settings from SettingsManager
                
            lock(cthreading.Lock):
                Thread lock for connecting with StreamtManager.

            max_no_data(int, Optional): 
                Maximum amout of time data check fails before disconnecting.
        """
        self._stream_manager:StreamManager = stream_manager
        self._get_pairs: callable = get_pairs
        self._get_settings: callable = get_settings

        self._loop_runtime = self._get_settings("klineStreamLoopRuntime")
        self._max_no_data = max_no_data
        #threading
        self._comm_lock = lock

        self._interval_index = 1
        self._interval = INTERVAL_LIST[self._interval_index]

        self._id_add : int = 0
        self._stream_id_list : list[str] = []

        self._active_streams: Dict[str, str] = {}

        self._backoff_attempt: int = 0
        self._error_count: int = 0
        self._data_error: bool = False
        self._time_old_data : int = 40 #in seconds
        self._data_error_time_reduction: int = 0
        self.count_no_data: int = 0
        self._strem_map = None

        self._time_ping: int = self._now()

        self._lock = threading.Lock()

        # self._logger
        # ----------------------------------------------------------------------
        self._logger = logging.getLogger("binance").getChild(self.__class__.__name__)
    # Public API 1 only
    # ==================================================================    
    # Run stream 
    # -----------------------------------------------------------------
    def run(self):
        """Run while loop that will only close on disconnect."""
        backoff_base = 1.5
        reconnectPause = 45
        
        disconnect = False
        while not disconnect:             
            
            self._error_count = 0
            self._data_error = False
            
            asyncio.run(self._connection_loop())
            
            with self._comm_lock:
                disconnect = self._stream_manager._disconnect    

            if not disconnect: #if shud down event is set no need to sleep
                # Backoff before attempting a clean fresh reconnect
                self._backoff_attempt += 1
                sleep_time = min(reconnectPause * (backoff_base ** (self._backoff_attempt - 1)), 300)
                msg = f"Binance StreamWorker stopped unexpectedly - restarting after {sleep_time} s"
                self._logger.error(msg) 
                print(msg) 
                time.sleep(sleep_time)
  
    # Core Loop
    # ==================================================================
    async def _connection_loop(self):
        global global_stream_connections
        self._logger.info("StreamWorker Starts the event loop")
        connection = None
        configuration_ws_streams = self._config()

        try:
            client = Spot(config_ws_streams=configuration_ws_streams)
            connection = await client.websocket_streams.create_connection()

            await asyncio.sleep(2)
            
            with self._lock:
                self._backoff_attempt: int = 0
                self.count_no_data = 0

                self._data_error_time_reduction = self._stream_manager.oldest()
                
                self._time_ping = self._now()

                self._logger.info("Connected")

            disconnect = False
            while not disconnect:

                with self._comm_lock:
                    self._stream_manager._connected = True
                    disconnect = self._stream_manager._disconnect

                with self._lock:
                    self._strem_map = global_stream_connections.stream_connections_map
                    requested_streams = self._build_requested_streams()
                    await self._subscribe_streams(connection, requested_streams)
                    await self._unsubscribe_streams(connection, requested_streams)

                    self._monitor_data_integrity()
                    await self._verify_server_subscriptions(connection)

                if self._data_error:
                    self._data_error = False
                    await self._global_cleanup()
                    #self._rotate_interval()
                    self._logger.warning(f"NO data -> global cleanup!")
                    await asyncio.sleep(5)
                    self._data_error_time_reduction = self._stream_manager.oldest()

                if self._error_count > 2:
                    self._logger.error(f"Too many errors {self._error_count} -> reconnect")
                    self._error_count = 0
                    break

                await asyncio.sleep(self._loop_runtime)

        except Exception as e:
            msg = f"Binance StreamWorker fatal error: {e}"
            self._logger.error(msg)
            print(msg)

        finally:            
            await self._cleanup(connection, client)
            connection = None
            client = None

    # Subscription Management
    # ==================================================================
    # Build requested list
    # -----------------------------------------------------------------
    def _build_requested_streams(self) -> Dict[str, str]:
        requested = {}
        for pair in self._get_pairs(filter_only="Binance").keys():
            requested[pair] = self._interval
        return requested

    # Stream subscription
    # -----------------------------------------------------------------
    async def _subscribe_streams(self, connection : SpotWebSocketStreams, requested_streams):      
        for pair in requested_streams:
            if pair not in self._active_streams:
                try:
                    # Generate unique ID for stream
                    random_uuid = uuid.uuid4()
                    self._id_add +=1
                    stream_id = f"{self._id_add}_ID_{random_uuid}"
                    self._stream_id_list.append(stream_id)
                    stream = await connection.kline(
                        symbol=pair,
                        interval=KlineIntervalEnum[f"INTERVAL_{self._interval}"].value,
                        id=str(random_uuid)                        
                    )
                    stream.on("message", self._on_message)
                    
                    self._active_streams[pair] = self._interval
                    self._logger.info(f"Subscribed to stream: {pair} | interval={self._interval}")
                    print(f"Subscribed to Binance stream: {pair} | interval={self._interval}")

                except Exception as e:
                    self._logger.error(f"Subscribe error {pair}: {e}")
                    self._error_count += 1
                    print(f"Binance StreamWorker error count: {self._error_count}")

    # Stream unsubscribe
    # -----------------------------------------------------------------
    async def _unsubscribe_streams(self, connection: SpotWebSocketStreams, requested_streams = {}):
        for pair in list(self._active_streams.keys()):
            if pair not in requested_streams:
                try:
                    stream_fmt = f"{pair.lower()}@kline_{self._active_streams[pair]}"
                    await connection.unsubscribe(streams=stream_fmt)
                    del self._active_streams[pair]

                    self._logger.info(f"Unsubscribed from stream: {pair}")
                    print(f"Binance Unsubscribed from stream: {pair}")
                except Exception as e:
                    self._logger.error(f"Unsubscribe error {pair}: {e}")
                    self._error_count += 1
                    print(f"Binance StreamWorker error count: {self._error_count}")

    # Monitoring & Integrity
    # ==================================================================    
    # Check data aging
    # -----------------------------------------------------------------
    def _monitor_data_integrity(self):
        time_old_data = self._time_old_data
        time_oldest = self._stream_manager.oldest()
        time_compare = time_oldest - self._data_error_time_reduction
        if (
            time_compare > time_old_data
            and self._stream_manager.all_streams_available()
        ):
            self.count_no_data += 1
            self._data_error_time_reduction = time_oldest
            if self.count_no_data > 0:
                timestamp_oldest = self._stream_manager.oldest_timestamp()
                self._logger.warning(
                    f"StreamWorker no data received: {self.count_no_data} | time oldest= {time_oldest} s | timestamp of oldest stream= {datetime.fromtimestamp(int(timestamp_oldest))} s"
                )
                self._time_ping = 0 # foce request subscription list

            if self.count_no_data > self._max_no_data:
                self._logger.error("StreamWorker data starvation detected")
                self._data_error = True
                self.count_no_data = 0
                #self._rotate_interval()
        if time_oldest < self._data_error_time_reduction:
            self.count_no_data = 0
            self._data_error_time_reduction = 0
            self._logger.info(f"New data recived. time oldest= {time_oldest} s")
            print("Binance Stream New data recived.")
    
    # Verfy subscriptions
    # -----------------------------------------------------------------
    async def _verify_server_subscriptions(self, connection : SpotWebSocketStreams ):
        now_seconds = self._now()
        if (
            (now_seconds - self._time_ping)
            > int(self._get_settings("pingUpdate") * 60)
            and self._stream_manager.all_streams_available()
        ):
            self._time_ping = now_seconds
            try:
                allSubs = await connection.list_subscribe()

                if len(self._active_streams) > len(allSubs["result"]):
                    self._logger.warning(
                        f"Subscription mismatch: server={allSubs['result']} "
                        f"local={self._active_streams}"
                    )
                    self._data_error = True
                    
                self._active_streams.clear()
                for sub in allSubs["result"]:
                    stream_pair, _, _ = sub.partition("@")
                    self._active_streams[stream_pair.upper()] = self._interval

            except Exception as e:
                self._logger.error(f"list_subscribe error: {e}")
                self._error_count += 1
                print(f"Binance StreamWorker error count: {self._error_count}")
    
    # Rotate interval
    # -----------------------------------------------------------------
    def _rotate_interval(self):
        self._interval_index = (self._interval_index + 1) % len(INTERVAL_LIST)
        self._interval = INTERVAL_LIST[self._interval_index]

        msg = f"Rotating Binance  stream interval -> new interval = {self._interval}"
        self._logger.warning(msg)
        print(msg)
 
    # Incoming Data Handler
    # ==================================================================
    def _on_message(self, data):
        try:
            if not data:
                return

            kline = StreamKline(
                time_ms=int(data.E),
                open_=float(data.k.o),
                close=float(data.k.c),
                high=float(data.k.h),
                low=float(data.k.l),
                volume=float(data.k.v),
                interval=data.k.i
            )
            with self._comm_lock:
                self._stream_manager.set(data.s, kline)

        except Exception as e:
            self._logger.error(f"Message parse error: {e}")

    # Cleanup
    # ==================================================================
    async def _cleanup(
        self,
        connection: SpotWebSocketStreams | None,
        client: Spot | None
    ):
        self._logger.warning("Starting websocket cleanup")

        # ---- 1. STOP NEW COMMANDS IMMEDIATELY ----
        with self._comm_lock:
            self._stream_manager._connected = False  # <-- your guards rely on this

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
        
        self._global_cleanup()
        self._active_streams.clear()

        self._logger.info("Cleanup complete")
        self._logger.info(f"After cleanup: connection: {connection} | client: {client}")
        print("Binance StreamWorker cleanup complete")

    # Delete from  global map IN Binance Lib!!!!
    # -----------------------------------------------------------------
    def _global_cleanup(self):
        try:
            for stream in list(self._strem_map.keys()):
                del self._strem_map[stream]
                self._logger.info(f"Global cleanup stream: {stream}")
                print(f"Binance StreamWorker global cleanup stream: {stream}")
        except Exception as e:
            self._logger.error(f"Global cleanup error {stream}: {e}")

    # Stream configuration
    # -----------------------------------------------------------------
    def _config(self) ->ConfigurationWebSocketStreams:
        configuration_ws_streams = ConfigurationWebSocketStreams(
            stream_url=os.getenv("STREAM_URL", SPOT_WS_STREAMS_PROD_URL),
            reconnect_delay= self._get_settings("reconnect_delay"),
            mode=WebsocketMode.SINGLE,
            pool_size=1
        )

        self._logger.info(
            f"StreamWorker config: stream_url={configuration_ws_streams.stream_url}, "
            f"reconnect_delay={configuration_ws_streams.reconnect_delay}, "
            f"mode={configuration_ws_streams.mode}, "
            f"pool_size={configuration_ws_streams.pool_size}"
        )
        return configuration_ws_streams

    # Utilities
    # ==================================================================
    @staticmethod
    def _now() -> int:
        return int(datetime.now(timezone.utc).timestamp())
