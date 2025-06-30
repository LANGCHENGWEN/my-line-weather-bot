# handlers/menu_weather.py
from linebot.v3.messaging.models import TextMessage, ReplyMessageRequest
from menu_handlers.settings_menu_handler import handle_settings_menu_postback
from urllib.parse import parse_qs
from utils.api_helper import get_messaging_api
from utils.line_common_messaging import send_line_reply_message
from utils.user_data_manager import set_user_state

def handle(event):
    data = parse_qs(event.postback.data)
    action = data.get("action", [""])[0]

    if action == "change_city":
        # 進入「等待使用者輸入城市」狀態
        weather_type = data.get("type", ["current"])[0]
        set_user_state(event.source.user_id, "awaiting_city_input", weather_type)

        api = get_messaging_api()
        send_line_reply_message(api,
            reply_token=event.reply_token,
            messages="請輸入您想查詢的縣市名稱，例如：台中市 或 台北市"
        )


'''
def handle(event):
    line_bot_api = get_messaging_api()
    if handle_forecast_postback(line_bot_api, event):
        return
    if handle_settings_menu_postback(line_bot_api, event):
        return
    # 其他 postback…
'''