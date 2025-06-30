from user_data_manager import is_valid_city, save_default_city, clear_user_state
from utils.api_helper import get_messaging_api
from linebot.v3.messaging.models import TextMessage, ReplyMessageRequest
from config import setup_logging
logger = setup_logging(__name__)

def handle(event):
    city = event.message.text.strip()

    line_bot_api = get_messaging_api()
    if is_valid_city(city):
        save_default_city(event.source.user_id, city)
        line_bot_api.reply_message(ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=f"預設城市已設為 {city}！")]
        ))
        clear_user_state(event.source.user_id)
        logger.info(f"已為 {event.source.user_id} 設定預設城市：{city}")
    else:
        line_bot_api.reply_message(ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text="請輸入有效城市，例如：台中市")]
        ))
        logger.info(f"用戶 {event.source.user_id} 輸入無效城市：{city}")