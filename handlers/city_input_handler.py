# handlers/city_input_handler.py
import logging
from functools import partial
from linebot.v3.messaging import ApiClient
from linebot.v3.messaging.models import TextMessage, ReplyMessageRequest
from linebot.v3.webhooks.models import MessageEvent

# from weather_forecast.forecast_options_flex import create_forecast_options_flex_message
from utils.api_helper import get_messaging_api
from utils.major_stations import ALL_TAIWAN_COUNTIES
from utils.text_processing import normalize_city_name
from utils.line_common_messaging import send_line_reply_message
from utils.user_data_manager import (
    is_valid_city,          # 判定縣市是否合法
    save_default_city,      # 儲存到 DB / 檔案
    clear_user_state,       # 清空 state
    get_user_state
)

from weather_today.today_handler import reply_today_weather_of_city
from weather_current.current_handler import reply_current_weather_of_city
from weather_forecast.forecast_handler import reply_forecast_weather_of_city

from outfit_suggestion.outfit_responses import reply_outfit_weather_of_city

logger = logging.getLogger(__name__)

def _process_city_input(api: ApiClient, event: MessageEvent, handler_function) -> bool:
    """
    通用函式：處理用戶輸入城市，並呼叫對應的處理邏輯。
    handler_function 是一個回調函式，接收 (api, reply_token, user_id, normalized_city)
    """
    user_id = event.source.user_id
    reply_token = event.reply_token
    user_input_city = event.message.text.strip()
    normalized_city = normalize_city_name(user_input_city)

    if is_valid_city(normalized_city):
        # 呼叫傳入的特定處理函式
        handler_function(api, reply_token, user_id, normalized_city)
        clear_user_state(user_id) # 清除狀態
        logger.info(f"用戶 {user_id} 查詢 {normalized_city}，狀態已清除。")
        return True # 處理成功
    else:
        send_line_reply_message(api, reply_token, [TextMessage(text="請輸入有效的台灣縣市名稱，例如：台中市 或 台北市")])
        logger.info(f"用戶 {user_id} 輸入無效城市: {user_input_city}，提示用戶重新輸入。")
        return False # 無效輸入，但已回覆，所以也返回 True 停止 text_router 繼續處理

# follow.py負責開始流程，這個檔案負責接收並完成流程
def handle_awaiting_default_city_input(api: ApiClient, event: MessageEvent) -> bool:
    """處理首次設定預設城市的輸入"""
    user_id = event.source.user_id
    reply_token = event.reply_token
    user_input_city = event.message.text.strip()
    normalized_city = normalize_city_name(user_input_city)

    # line_bot_api = get_messaging_api()
    if is_valid_city(normalized_city):
        save_default_city(user_id, normalized_city)
        send_line_reply_message(api, reply_token, [TextMessage(text=f"已將預設城市設定為：{normalized_city}！\n您可以開始查詢天氣了。")])
        clear_user_state(user_id)
        logger.info(f"已為 {user_id} 設定預設城市：{normalized_city}，狀態已清除。")
        return True # 處理完畢，返回 True
    else:
        send_line_reply_message(api, reply_token, [TextMessage(text="請輸入有效的台灣縣市名稱，例如：台中市 或 台北市")])
        logger.info(f"用戶 {user_id} 輸入無效城市：{user_input_city}，提示用戶重新輸入。")
        return False # 無效輸入，提示用戶重試，但讓 text_router 停止
    
# ---------- 處理用戶輸入城市並查詢今日天氣 ----------
def handle_awaiting_today_city_input(api: ApiClient, event: MessageEvent) -> bool:
    """處理今日天氣查詢其他城市的輸入"""
    # 這裡的 reply_today_weather_of_city 應在 today_handler.py 中實現
    # 並且它應該接收 (api, reply_token, user_id, city) 參數來回覆
    return _process_city_input(api, event, reply_today_weather_of_city)

# ---------- 處理用戶輸入城市並查詢即時天氣 ----------
def handle_awaiting_city_input(api: ApiClient, event: MessageEvent) -> bool:
    """處理即時天氣查詢其他城市的輸入"""
    # 這裡的 reply_current_weather_of_city 應在 current_handler.py 中實現
    # 並且它應該接收 (api, reply_token, user_id, city) 參數來回覆
    return _process_city_input(api, event, reply_current_weather_of_city)

# ---------- 處理用戶輸入城市並查詢未來預報  (顯示天數選單)----------
def handle_awaiting_forecast_city_input(api: ApiClient, event: MessageEvent) -> bool:
    """
    處理未來預報查詢其他城市的輸入。
    此函式應呼叫一個能夠顯示天數選單的函式，並將用戶輸入的城市傳遞過去。
    """
    # 🚀 這裡呼叫的是用來發送天數選單的函式
    return _process_city_input(api, event, reply_forecast_weather_of_city)
    
# ---------- 處理用戶輸入城市並查詢穿搭建議 ----------
def handle_awaiting_outfit_city_input(api: ApiClient, event: MessageEvent) -> bool:
    """處理穿搭建議查詢其他城市的輸入"""
    # 這裡的 reply_outfit_weather_of_city 應在 outfit_handler.py 中實現
    return _process_city_input(api, event, reply_outfit_weather_of_city)