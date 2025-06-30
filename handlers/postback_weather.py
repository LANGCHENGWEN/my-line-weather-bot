# handlers/postback_weather.py
from linebot.v3.messaging.models import TextMessage, ReplyMessageRequest
from config import setup_logging
from menu_handlers.settings_menu_handler import handle_settings_menu_postback
from urllib.parse import parse_qs
from utils.api_helper import get_messaging_api
from utils.line_common_messaging import send_line_reply_message
from utils.user_data_manager import set_user_state, set_user_metadata, get_user_metadata

logger = setup_logging(__name__)

def handle(event):
    """只處理 weather 類型的 postback"""
    logger.info(f"Received postback: {event.postback.data}")
    data = parse_qs(event.postback.data)
    action = data.get("action", [""])[0]

    if action == "weather_query":
        # 例如顯示子選單，或直接回即時天氣
        pass

    elif action == "typhoon_area":
        # 例如顯示颱風資訊
        pass

    elif action == "lifestyle_reminders":
        # 例如顯示生活提醒
        pass

    elif action == "settings":
        # 例如顯示設定選單
        return

    elif action == "change_city":
        logger.debug(f"Attempting to set user state to awaiting_city_input for {event.source.user_id}")
        # weather_type = data.get("type", ["current"])[0]
        set_user_state(event.source.user_id, "awaiting_city_input")
        logger.debug(f"User state should now be awaiting_city_input for {event.source.user_id}")

        # set_user_metadata(event.source.user_id, weather_type=weather_type)

        logger.info(f"設定 user {event.source.user_id} 狀態為: awaiting_city_input")
        # weather_type = get_user_metadata(event.source.user_id, "weather_type", "current")

        api = get_messaging_api()
        send_line_reply_message(api,
            reply_token=event.reply_token,
            messages=[TextMessage(text="請輸入您想查詢的縣市名稱，例如：台中市 或 台北市")]
        )
        logger.info(f"user {event.source.user_id} → awaiting_city_input")

'''
def handle(event):
    line_bot_api = get_messaging_api()
    if handle_forecast_postback(line_bot_api, event):
        return
    if handle_settings_menu_postback(line_bot_api, event):
        return
    # 其他 postback…
'''