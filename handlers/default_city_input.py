# default_city_input
import logging
from linebot.v3.messaging.models import TextMessage, ReplyMessageRequest

from weather_current.current_handler import reply_weather_of_city
from utils.api_helper import get_messaging_api
from utils.line_common_messaging import send_line_reply_message
from utils.user_data_manager import (
    is_valid_city,          # 判定縣市是否合法
    save_default_city,      # 儲存到 DB / 檔案
    clear_user_state,       # 清空 state
    set_user_state          # 若要切回別的 state
)

logger = logging.getLogger(__name__)

def handle(line_bot_api, event):
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

# ---------- 「查詢其他縣市」 ----------
def handle_awaiting_city_input(api, event):
    """
    state = awaiting_city_input 時呼叫
    """
    city        = event.message.text.strip()
    api         = get_messaging_api()
    user_id     = event.source.user_id
    reply_token = event.reply_token

    if is_valid_city(city):
        # 在這裡呼叫你即時天氣 / 未來預報的主程式，
        #   把 city 當參數傳入並產生 Flex 或文字 -> 回覆
        # 例：weather_current.current_handler.reply_weather_of_city(api, reply_token, city)
        # ▼ 直接呼叫，馬上回 Flex
        reply_weather_of_city(api, reply_token, city)

        clear_user_state(user_id)      # 或轉回別的 state
        logger.info(f"[OtherCity] {user_id} 查詢 {city}")
    else:
        send_line_reply_message(api, reply_token,
            [TextMessage(text="請輸入有效城市，例如：台中市 或 台北市")])
        logger.info(f"[OtherCity] 無效輸入: {city}")