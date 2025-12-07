from src.settings import settings_obj
from src.constants import(
    LOG_PATH_BINANCE_API
)
import asyncio
import os
import logging
from telegram import Bot

# Create a logger for this module
logger = logging.getLogger(__name__)

#Send telegram message
async def _telegram_send(text):
    try:
        telegram_token, telegram_chatID = _get_telegram_settings()
        bot = Bot(token=telegram_token       
        )
        await bot.send_message(chat_id=telegram_chatID, text=text)
    except Exception as e:
        logger.error(f"telegramSend() error: {e}")

#Get Telegram TOKEN and chatID from file or enviroment
def _get_telegram_settings():
    try:
        #Get keys from inviroment variables if not defined
        telegram_token = settings_obj.get("telegram_TOKEN")
        telegram_chat_id = settings_obj.get("telegram_chatID")
        if "telegram_TOKEN" in telegram_token:
            telegram_token = os.environ.get("TELEGRAM_TOKEN")
        if "telegram_chatID" in telegram_chat_id:
            telegram_chat_id = os.environ.get("TELEGRAM_CHATID")

        return telegram_token, telegram_chat_id
    except Exception as e:
        logger.error(f"_getTelegramTOKEN() error: {e}")

def send_telegram_msg(msg:str):
    """
    Args:
        msg(str):
            Message to send vial telegram bot.
    """
    if settings_obj.get("useTelegram"):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        task = None 
        try:
            task = loop.create_task(_telegram_send(msg))            
            loop.run_until_complete(task)
            loop.close()
        except Exception as e:
            logger.error(f"telegramSend() error: {e}")