import json
import threading
import time
import queue
import websockets
from websockets import ClientConnection
import asyncio
import logging

HERMES_WS_URL = "wss://hermes.pyth.network/ws"

class PythStream:
    """
    Pyth Stream Manager Subscribe/Unsubscribe by ids() and reconnect
    """
    def __init__(self, logger_name="pyth"):
        """
        Args:
            logger_name(str, Optional):
                Name of the logger. Default is pyth.
        """
        self.reconnect_pause = 30
        self._subs = {}                 # feed_id -> callback
        self._send_q = asyncio.Queue()
        self._ping_e = asyncio.Event()
        self._last_ping = None
        self._disconnect_event = asyncio.Event()        
        self._shutdown = False
        self._connected = False
        self._loop = None
        self._connection : ClientConnection = None
        self._lock = threading.Lock()
        self._thread = threading.Thread(
            target=self._run,
            daemon=True
            )
    
        # --- Logger Setup ---
        self._logger = logging.getLogger(logger_name).getChild(self.__class__.__name__)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self._clenup()
        
    # ---------- Public API ----------

    def start(self):
        """ Start internal thread """
        self._thread.start()
        
    def shutdown(self):
        """ Shutdown loop and thread"""
        self._clenup()

    def ping(self):
        """
        Poing serve. in no ping response force reconnection.
        """
        with self._lock:
            if self._connection:
                self._ping_e.set()
            i = 10 # timout exit
            while self._ping_e.is_set() and i>0:
                time.sleep(1)
                i -=1

            return self._last_ping
    def reconnect(self):
        """
        Force disconnect. Reconnecting automaticaly.
        """
        if not self._loop:
            return

        def _stop_loop():
            self._disconnect_event.set()

        self._loop.call_soon_threadsafe(_stop_loop)

    def subscribe(self, feed_id: str, callback: callable):
        """
        Args:
            feed_id(str):
                Id of feed acquired trough https://hermes.pyth.network/v2/price_feeds
            callback(callable):
                Function to call when stream is recived 
        """        
        try:
            with self._lock:
                if not self._connected:
                    return
                self._subs[feed_id] = callback
                self._send_subscribe([feed_id])
        except Exception as e:
            self._logger.error(f"subscribe() error: {e}")

    def unsubscribe(self, feed_id: str):
        """
        Args:
            feed_id(str):
                Id of feed acquired trough https://hermes.pyth.network/v2/price_feeds            
        """
        try:
            with self._lock:
                if not self._connected:
                    return
                self._subs.pop(feed_id, None)
                self._send_unsubscribe([feed_id])
        except Exception as e:
            self._logger.error(f"unsubscribe() error: {e}")

    def get_active_subs(self) -> list[str]:
        """
        Returns:
            list[str]:
                List of feed ids          
        """
        with self._lock:
            return list(self._subs.keys())

    def is_connected(self) ->bool:
        """Returns:
            bool: 
                connection status
        """
        with self._lock:
            return self._connected
    # ---------- Internals ----------

    def _send_subscribe(self, ids):
        if not self._loop:
            return
        self._loop.call_soon_threadsafe(
            self._send_q.put_nowait,
            {
                "type": "subscribe",
                "ids": ids
            })

    def _send_unsubscribe(self, ids):
        if not self._loop:
            return
        self._loop.call_soon_threadsafe(
            self._send_q.put_nowait,
            {
                "type": "unsubscribe",
                "ids": ids
            })

    def _run(self):
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

            self._loop.run_until_complete(self._ws_loop())

            self._loop.run_until_complete(self._loop.shutdown_asyncgens())
            self._loop.close()
            print("End of PythStream thread")
        except Exception as e:
            self._logger.error(f"_run() error: {e}")

    async def _ws_loop(self):     
        backoff_base = 1.5
        backoff_attempt = 0
        print("Start of Pyth stream loop")
        self._logger.info("Start of stream loop")
        try:
            while not self._shutdown:         

                sleep_time = min(self.reconnect_pause * (backoff_base ** (backoff_attempt)), 300)
                try:
                    async with websockets.connect(
                        HERMES_WS_URL,
                        ping_interval=None,
                    ) as ws:
                        backoff_attempt = 0
                        with self._lock:
                            self._connection = ws
                            self._connected = True
                        # Reconnect
                        if self._subs:
                            await ws.send(json.dumps({
                                "type": "subscribe",
                                "ids": list(self._subs.keys())
                            }))
                        tasks : list[asyncio.Task] = []
                        tasks.append(asyncio.create_task(self._recv()))
                        tasks.append(asyncio.create_task(self._send()))
                        tasks.append(asyncio.create_task(self._ping()))

                        await self._disconnect_event.wait()     
                        self._disconnect_event.clear()
                        with self._lock:
                            self._connected = False
                            
                        for t in tasks:
                            t.cancel()

                        await asyncio.gather(*tasks, return_exceptions=True)
                        await ws.close()        

                except websockets.ConnectionClosed:
                    if not self._shutdown:                          
                        await asyncio.sleep(sleep_time)                

                except Exception as e:
                    self._logger.error(f"WS error: {e} / reconnecting in {sleep_time} s")
                    print(f"Pyth WS error: {e} / reconnecting in {sleep_time} s")
                    await asyncio.sleep(sleep_time)

                finally:                    
                    if not self._shutdown:                        
                        self._logger.warning(f"Disconnected — reconnecting in {sleep_time} s") 
                        print(f"Pyth Stream Disconnected — reconnecting in {sleep_time} s") 
                    backoff_attempt += 1
                    with self._lock:
                        self._connection = None
                        self._connected = False
                
        finally:                
            with self._lock:
                self._connection = None
                self._connected = False      
            self._logger.info("Shutdown complete")

    async def _send(self):
        while not self._shutdown:
            try:
                ws = self._connection
                msg = await self._send_q.get()
            except asyncio.CancelledError:
                break
            await ws.send(json.dumps(msg))

    async def _ping(self, watchdog: int = 1):
        while not self._shutdown:
            await asyncio.sleep(watchdog)
            ws = self._connection
            if self._ping_e.is_set() and False:     
                if ws:
                    try:
                        pong_await = await ws.ping()
                        resp = await pong_await
                        self._last_ping = resp
                        if not resp:
                            self._disconnect_event.set()
                    except Exception as e:
                        self._logger.exception(f"Pyth Ping error: {e} response {resp}")
                        self._disconnect_event.set()    
                                        
            self._ping_e.clear()   

    async def _recv(self):
        ws = self._connection
        async for msg in ws:
            self._handle_message(msg)

    def _clenup(self):
        self._shutdown = True

        if not self._loop:
            return

        def _stop_loop():
            self._disconnect_event.set()

        self._loop.call_soon_threadsafe(_stop_loop)        
        self._thread.join(timeout=10)

    # ---------- Message routing ----------

    def _handle_message(self, raw):
        data = json.loads(raw)
        if data.get("type") != "price_update":
            return
        
        update= data["price_feed"]
        feed_id = update["id"]
        cb = self._subs.get(feed_id)

        if cb:
            try:
                cb(update)
            except Exception:
                self._logger.exception("Callback error")
