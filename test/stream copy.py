# stream.py
# ======================================================================

from src.settings import StrategyManager, SettingsManager
from src.telegram import send_telegram_msg
from src.constants import INTERVAL_LIST

import logging
import asyncio
import os
import threading
import time
from datetime import datetime, timezone
from typing import Dict

from binance_sdk_spot.spot import (
    Spot,
    SPOT_WS_STREAMS_PROD_URL,
    ConfigurationWebSocketStreams,
    SpotWebSocketStreams
)
from binance_common.constants import WebsocketMode
from binance_sdk_spot.websocket_streams.models import KlineIntervalEnum





# ======================================================================
#                           STREAM WORKER
# ======================================================================

class StreamWorker:
    """
    Long-living Binance kline stream worker.
    """

    def __init__(
        self,
        log_path: str,
        stream_data : StreamManager,
        generate_pairs_intervals : function,
        get_settings : function,
        max_no_data: int = 10,
        init_interval_ind: int = 1

    ):
        self._stream_data = stream_data
        self._generate_pairs_intervals = generate_pairs_intervals
        self._get_settings = get_settings

        self._path= log_path
        self._loop_runtime = self._get_settings("klineStreamLoopRuntime")
        self._max_no_data = max_no_data

        self._interval_index = init_interval_ind % len(INTERVAL_LIST)
        self._interval = INTERVAL_LIST[self._interval_index]

        self._client: Spot | None = None
        self._connection = None

        self._active_streams: Dict[str, str] = {}
        self._connected: bool = False
        self._cmd_disconnect: bool = False

        self._backoff_attempt: int = 0
        self._error_count: int = 0
        self._data_error: bool = False

        self.time_ping: int = self._now()
        self.count_no_data: int = 0

        self._lock = threading.Lock()

        # ----------------------------------------------------------------------
        # self._logger
        # ----------------------------------------------------------------------
        self._logger = logging.getLogger(__name__)
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False

        _file_handler = logging.FileHandler(self._path)
        _formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        _file_handler.setFormatter(_formatter)

        if not self._logger.handlers:
            self._logger.addHandler(_file_handler)

    # Public API
    # ==================================================================    
    # Run stream 
    # -----------------------------------------------------------------
    def run(self):
        """Run while loop that will only close on disconnect."""
        backoff_base = 1.5
        reconnectPause = 30

        while not self._cmd_disconnect:            
            self._create_async_loop()

            if not self._cmd_disconnect: #if shud down event is set no need to sleep
                # Backoff before attempting a clean fresh reconnect
                self._backoff_attempt += 1
                sleep_time = min(reconnectPause * (backoff_base ** (self._backoff_attempt - 1)), 300)
                msg = f"StreamWorker() stopped unexpectedly - restarting after {sleep_time} s"
                self._logger.error(msg) 
                print(msg) 
                time.sleep(sleep_time) 

    # Disconnect
    # -----------------------------------------------------------------
    def disconnect(self):
        """Signal stream to disconnect."""
        self._logger.info("StreamWorker.stop() requested")
        with self._lock:
            self._cmd_disconnect = True

    # check connection status
    # -----------------------------------------------------------------
    def is_connected(self) -> bool:
        return self._connected


    # Async loop creation  
    # ---------------------------------------------------------  
    def _create_async_loop(self):   
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        task = None
        #Runn loop for Websocet_loop   
        try:
            task = loop.create_task(self._connection_loop())        
            loop.run_until_complete(task)
        except Exception as e:
            self._logger.error(f"StreamWorker(): top-level exception: {e}")
            print(f"StreamWorker(): top-level exception: {e}")

        # Cancel any remaining tasks before closing the loop
        pending = asyncio.all_tasks(loop=loop)
        for t in pending:
            t.cancel()
        loop.run_until_complete(asyncio.gather(*asyncio.all_tasks(loop), return_exceptions=True))
        loop.close() 
        self._logger.warning(f"StreamWorker(): cancelling {len(pending)} pending tasks")

    # Core Loop
    # ==================================================================
    async def _connection_loop(self):
        connection_stream = None

        configuration_ws_streams = self._config()

        try:
            client = Spot(config_ws_streams=configuration_ws_streams)
            connection_stream = await client.websocket_streams.create_connection()

            await asyncio.sleep(2)
            self._backoff_attempt: int = 0

            self._connected = True
            self.time_ping = self._now()

            self._logger.info("StreamWorker connected")

            while not self._cmd_disconnect:
                with self._lock:
                    requested_streams = self._build_requested_streams()
                    await self._subscribe_streams(connection_stream, requested_streams)
                    await self._unsubscribe_streams(connection_stream, requested_streams)

                    self._monitor_data_integrity()
                    await self._verify_server_subscriptions(connection_stream)

                if self._data_error:
                    self._rotate_interval()
                    await asyncio.sleep(10)

                if self._error_count > 2:
                    self._logger.error("StreamWorker too many errors -> reconnect")
                    break

                await asyncio.sleep(self._loop_runtime)

        except Exception as e:
            msg = f"StreamWorker fatal error: {e}"
            self._logger.error(msg)
            print(msg)
            send_telegram_msg(msg)

        finally:
            self._connected = False
            await self._cleanup(connection_stream)

    # Subscription Management
    # ==================================================================
    # Build requested list
    # -----------------------------------------------------------------
    def _build_requested_streams(self) -> Dict[str, str]:
        requested = {}
        for pair in self._generate_pairs_intervals().keys():
            requested[pair] = self._interval
        return requested

    # Stream subscription
    # -----------------------------------------------------------------
    async def _subscribe_streams(self, connection : SpotWebSocketStreams, requested_streams):
        for pair in requested_streams:
            if pair not in self._active_streams:
                try:
                    stream = await connection.kline(
                        symbol=pair,
                        interval=KlineIntervalEnum[f"INTERVAL_{self._interval}"].value,
                    )
                    stream.on("message", self._on_message)

                    self._active_streams[pair] = self._interval
                    self._logger.info(f"Subscribed to stream: {pair} | interval={self._interval}")
                
                except Exception as e:
                    self._logger.error(f"Subscribe error {pair}: {e}")
                    self._error_count += 1
                    print(f"StreamWorker error count: {self._error_count}")

    # Stream unsubscribe
    # -----------------------------------------------------------------
    async def _unsubscribe_streams(self, connection: SpotWebSocketStreams, requested_streams):
        for pair in list(self._active_streams.keys()):
            if pair not in requested_streams:
                try:
                    stream_fmt = f"{pair.lower()}@kline_{self._active_streams[pair]}"
                    await connection.unsubscribe(streams=stream_fmt)
                    del self._active_streams[pair]

                    self._logger.info(f"Unsubscribed from stream: {pair}")
                except Exception as e:
                    self._logger.error(f"Unsubscribe error {pair}: {e}")
                    self._error_count += 1
                    print(f"StreamWorker error count: {self._error_count}")

    # Monitoring & Integrity
    # ==================================================================    
    # Check data aging
    # -----------------------------------------------------------------
    def _monitor_data_integrity(self):
        time_old_data = 20

        if (
            self._stream_data.oldest() > time_old_data
            and self._stream_data.all_streams_available()
        ):
            self.count_no_data += 1

            if self.count_no_data > 0:
                self._logger.warning(
                    f"StreamWorker no data received: {self.count_no_data}"
                )
                self.time_ping = 0

            if self.count_no_data > self._max_no_data:
                self._logger.error("StreamWorker data starvation detected")
                self._data_error = True
                self.count_no_data = 0

    # Verfy subscriptions
    # -----------------------------------------------------------------
    async def _verify_server_subscriptions(self, connection : SpotWebSocketStreams ):
        now_seconds = self._now()
        if (
            (now_seconds - self.time_ping)
            > int(self._get_settings("pingUpdate") * 60)
            and self._stream_data.all_streams_available()
        ):
            self.time_ping = now_seconds
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
                print(f"StreamWorker error count: {self._error_count}")

    # Rotate interval
    # -----------------------------------------------------------------
    def _rotate_interval(self):
        self._interval_index = (self._interval_index + 1) % len(INTERVAL_LIST)
        self._interval = INTERVAL_LIST[self._interval_index]
        self._data_error = False

        msg = f"Rotating stream interval -> new interval = {self._interval}"
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

            self._stream_data.set(data.s, kline)

        except Exception as e:
            self._logger.error(f"StreamWorker message parse error: {e}")

    # Cleanup
    # ==================================================================
    async def _cleanup(self, connection: SpotWebSocketStreams):
        try:
            if connection:
                await asyncio.wait_for(
                    connection.close_connection(close_session=True),
                    timeout=10,
                )
        except Exception as e:
            self._logger.error(f"StreamWorker close connection error: {e}")

        try:
            if self._client and hasattr(self._client, "close_connections"):
                await asyncio.wait_for(
                    self._client.close_connections(),
                    timeout=10,
                )
        except Exception as e:
            self._logger.error(f"StreamWorker close client error: {e}")

        pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if pending:
            self._logger.warning(f"StreamWorker cancelling {len(pending)} pending tasks")
            for t in pending:
                try:
                    t.cancel()
                except Exception:
                    pass
            await asyncio.gather(*pending, return_exceptions=True)

        self._client = None
        self._logger.info("StreamWorker cleanup complete")

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
