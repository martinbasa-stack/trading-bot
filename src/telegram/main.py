from src.settings.main import credentials_obj, settings_obj

from .service import TelegramService
from .on_message import on_message_response

telegram_obj = TelegramService(
    settings_get=settings_obj.get,
    credentials_get=credentials_obj.get,
    on_message=on_message_response
)