# default_city_input.py
import logging
from linebot.v3.messaging.models import TextMessage, ReplyMessageRequest

# from weather_forecast.forecast_options_flex import create_forecast_options_flex_message
from utils.api_helper import get_messaging_api
from utils.major_stations import ALL_TAIWAN_COUNTIES
from utils.text_processing import normalize_city_name
from utils.line_common_messaging import send_line_reply_message
from utils.user_data_manager import (
    is_valid_city,          # 判定縣市是否合法
    save_default_city,      # 儲存到 DB / 檔案
    clear_user_state,       # 清空 state
    set_user_state          # 若要切回別的 state
)

from weather_today.today_handler import reply_today_weather_of_city
from weather_current.current_handler import reply_current_weather_of_city
from weather_forecast.forecast_handler import reply_forecast_weather_of_city

logger = logging.getLogger(__name__)

# follow.py負責開始流程，這個檔案負責接收並完成流程
def handle(line_bot_api, event):
    city = event.message.text.strip()
    normalized_city = normalize_city_name(city)

    line_bot_api = get_messaging_api()
    if is_valid_city(normalized_city):
        save_default_city(event.source.user_id, normalized_city)
        line_bot_api.reply_message(ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=f"預設城市已設為 {normalized_city}！")]
        ))
        clear_user_state(event.source.user_id)
        logger.info(f"已為 {event.source.user_id} 設定預設城市：{normalized_city}")
    else:
        line_bot_api.reply_message(ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text="請輸入有效城市，例如：台中市 或 台北市")]
        ))
        logger.info(f"用戶 {event.source.user_id} 輸入無效城市：{city}")

# ---------- 處理用戶輸入城市並查詢今日天氣 ----------
def handle_awaiting_today_city_input(api, event):
    """
    state = awaiting_city_input 時呼叫
    """
    city        = event.message.text.strip()
    normalized_city = normalize_city_name(city)

    # api         = get_messaging_api()
    user_id     = event.source.user_id
    reply_token = event.reply_token

    if is_valid_city(normalized_city):
        # 在這裡呼叫你即時天氣 / 未來預報的主程式，
        #   把 city 當參數傳入並產生 Flex 或文字 -> 回覆
        # 例：weather_current.current_handler.reply_weather_of_city(api, reply_token, city)
        # ▼ 直接呼叫，馬上回 Flex
        reply_today_weather_of_city(api, reply_token, normalized_city)

        clear_user_state(user_id)      # 或轉回別的 state
        logger.info(f"[OtherCity] {user_id} 查詢 {normalized_city} 的今日天氣，狀態已清除。")
        return True
    else:
        send_line_reply_message(api, reply_token,
            [TextMessage(text="請輸入有效城市，例如：台中市 或 台北市")])
        logger.info(f"[OtherCity] 無效輸入: {city}，提示用戶重新輸入。")
        return True

# ---------- 處理用戶輸入城市並查詢即時天氣 ----------
def handle_awaiting_city_input(api, event):
    """
    state = awaiting_city_input 時呼叫
    """
    city        = event.message.text.strip()
    normalized_city = normalize_city_name(city)

    # api         = get_messaging_api()
    user_id     = event.source.user_id
    reply_token = event.reply_token

    if is_valid_city(normalized_city):
        # 在這裡呼叫你即時天氣 / 未來預報的主程式，
        #   把 city 當參數傳入並產生 Flex 或文字 -> 回覆
        # 例：weather_current.current_handler.reply_weather_of_city(api, reply_token, city)
        # ▼ 直接呼叫，馬上回 Flex
        reply_current_weather_of_city(api, reply_token, normalized_city)

        clear_user_state(user_id)      # 或轉回別的 state
        logger.info(f"[OtherCity] {user_id} 查詢 {normalized_city} 的即時天氣，狀態已清除。")
        return True
    else:
        send_line_reply_message(api, reply_token,
            [TextMessage(text="請輸入有效城市，例如：台中市 或 台北市")])
        logger.info(f"[OtherCity] 無效輸入: {city}，提示用戶重新輸入。")
        return True

# ---------- 處理用戶輸入城市並查詢未來預報 ----------
def handle_awaiting_forecast_city_input(api, event):
    """
    state = awaiting_forecast_city_input 時呼叫
    """
    city        = event.message.text.strip()
    normalized_city = normalize_city_name(city)

    user_id     = event.source.user_id
    reply_token = event.reply_token

    if is_valid_city(normalized_city):
        reply_forecast_weather_of_city(api, reply_token, normalized_city)
        # flex_msg = handle_forecast_message(city)
        # send_line_reply_message(api, reply_token, [flex_msg])

        clear_user_state(user_id)      # 或轉回別的 state
        logger.info(f"[OtherCity] {user_id} 查詢 {normalized_city} 的未來預報，狀態已清除。")
        return True
    else:
        send_line_reply_message(api, reply_token,
            [TextMessage(text="請輸入有效城市，例如：台中市 或 台北市")])
        logger.info(f"[OtherCity] 無效輸入: {city}，提示用戶重新輸入。")
        return True