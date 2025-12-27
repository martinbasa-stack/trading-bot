import asyncio
import threading
import os
import logging

from .response_utils import status_msg, strategy_status, active_strategy_list, last_trade, num_trades, get_local_ip, strategy_ids

from telegram import Update
from telegram.error import NetworkError
from telegram.request import HTTPXRequest
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackContext,
    MessageHandler,
    ContextTypes,
    filters
)
logging.getLogger("httpx").setLevel(logging.WARNING)
class TelegramService:
    """ Telegram Bot for sending and reciving messages"""
    def __init__(
            self, 
            settings_get: callable, 
            credentials_get: callable,
            on_message: callable
            ):
        """
        Args:
            settings_get(callable):
                Retrive settings parameter.
            credentials_get(callable):
                Retrive credentials (TOKEN and ChatID).
            on_message(callable(str)):
                Function to be called on recieving a message:
                    If return not None the return will be 'send' by bot.
        """
        self._on_message : callable = on_message
        self._settings_get : callable = settings_get
        self._credentials_get : callable = credentials_get
        self._shutdown = asyncio.Event()
        self._send_msg_q = asyncio.Queue()
        self._recive_msg_q = asyncio.Queue()
        self._tasks: list[asyncio.Task] = []
        self._app = None
        self._bot = None        
        self._chat_id = ""
        self._token = ""

        self._lock = threading.Lock()
        
        self._logger = logging.getLogger("app").getChild(self.__class__.__name__)

        self.loda_settings()

    def loda_settings(self):
        """ Load credentials."""
        with self._lock:
            #Get keys from inviroment variables if not defined
            self._toke = self._credentials_get("telegram_TOKEN", "telegram_TOKEN")
            self._chat_id = self._credentials_get("telegram_chatID", "telegram_chatID")
            if "telegram_TOKEN" in self._toke:
                self._toke = os.environ.get("TELEGRAM_TOKEN")
            if "telegram_chatID" in self._chat_id:
                self._chat_id = os.environ.get("TELEGRAM_CHATID")

    def send_msg(self, msg:str):
        """
        If telegram message is enabled will send a message.
        Args:
            msg(str):
                Message.
        """
        with self._lock:            
            try:
                if self._settings_get("useTelegram"):
                    self._send_msg_q.put_nowait(msg)
            except Exception as e:
                self._logger.error(f"send_msg() error: {e}")

    def recive_cmd(self) -> dict:
        """
        Check if any message was recived.
        Returns:
            dict:
                If no mse returns False else:
                    {
                    "cmd" : text,
                    "val" : 0
                    }
        
        """
        with self._lock:
            try:
                return self._recive_msg_q.get_nowait()
            except Exception: #If query empty return false
                return False

    async def start(self, shutdown: asyncio.Event):
        """
        Start telegram app and services. 
        Args:
            shutdown(asyncio.Event):
                Event for shut down.
        """
        try:
            self._configure_telegram_logging()
            self._shutdown = shutdown            
            self._tasks.append(asyncio.create_task(self._run_app()))
            self._tasks.append(asyncio.create_task(self._send()))

        except Exception as e:
            self._logger.error(f"start() error: {e}")
 
    # Stop Telegram service
    # -----------------------------------------------------------------------
    async def stop(self):
        try:         
            for t in self._tasks:                
                t.cancel()            
            print(self._tasks)

        except Exception as e:            
            self._logger.error(f"stop() error: {e}")

        finally:
            try:
                await asyncio.gather(*self._tasks, return_exceptions=True)
            except Exception as e:
                self._logger.error(f"stop() asyncio.gather error: {e}")        
        
    # Main Bot app creation     
    # -----------------------------------------------------------------------
    async def _run_app(self):
        while not self._shutdown.is_set():
            try:
                self._app = (
                    ApplicationBuilder()
                    .token(self._toke)
                    .request(
                        HTTPXRequest(
                            connect_timeout=10,
                            read_timeout=10,
                            write_timeout=10,
                            pool_timeout=10,
                        )
                    )
                    .build()
                )
                
                self._app.add_error_handler(self._error_handler)
                self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text))
                
                await self._app.initialize()
                await self._app.start()
                await self._app.updater.start_polling(
                    poll_interval=4,
                    allowed_updates=None,
                    )

                # Wait until shutdown
                await self._shutdown.wait()

            except NetworkError as e:
                self._logger.warning(f"Telegram network error: {e}")
                await asyncio.sleep(5)

            except Exception as e:
                self._logger.exception(f"Telegram fatal error: {e}")
                await asyncio.sleep(5)

            finally:
                try:
                    self._logger.info("Stopping Telegram app")
                    await self._app.stop()
                    await self._app.shutdown()
                except Exception:
                    pass

    async def _error_handler(self, update, context:CallbackContext ):
        print(context)
        err = context.error
        print(err)
        if isinstance(err, NetworkError):
            self._logger.warning(f"Telegram network issue: {err}")
        else:
            self._logger.exception("Telegram error", exc_info=err)


    # Send telegram message
    async def _send(self):
        while not self._shutdown.is_set():
            try:
                msg = await self._send_msg_q.get()
                await asyncio.wait_for(self._app.bot.send_message(chat_id=self._chat_id, text=msg, connect_timeout=5.0, write_timeout=5.0), timeout=6.0)
            except Exception as e:
                self._logger.error(f"_send() error: {e}")

    # Recive telegram message in text
    async def _handle_text(self,update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if str(update.effective_chat.id) != str(self._chat_id):
                return

            text = update.message.text.lower().strip()

            msg = self._on_message(text)
            if msg:
                self.send_msg(msg)
        except Exception as e:
            self._logger.error(f"handle_text error: {repr(e)}")


    # Silence the telegram official logger
    @staticmethod
    def _configure_telegram_logging():
        noisy_loggers = [
            "telegram",
            "telegram.ext",
            "telegram.ext._utils.networkloop",
            "telegram.ext._updater",
            "telegram.request",
            "httpx",
            "httpcore",
        ]

        for name in noisy_loggers:
            logger = logging.getLogger(name)
            logger.setLevel(logging.WARNING)
            logger.propagate = True   # keep routing to your handlers


