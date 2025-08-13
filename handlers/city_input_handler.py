# handlers/city_input_handler.py
"""
這個檔案主要負責處理使用者輸入縣市名稱後的各種情境。
當使用者在進行特定流程（例如：設定預設城市、查詢今日天氣、查詢未來預報、查詢穿搭建議等）時，會根據使用者輸入的縣市名稱進行驗證，並呼叫對應的業務邏輯函式來回覆使用者。
透過一個通用的處理函式來減少重複程式碼，讓不同功能的縣市輸入處理邏輯保持一致。
"""
import logging
from linebot.v3.messaging import ApiClient
from linebot.v3.messaging.models import TextMessage
from linebot.v3.webhooks.models import MessageEvent

from utils.text_processing import normalize_city_name
from utils.line_common_messaging import send_line_reply_message
from utils.firestore_manager import (
    is_valid_city,    # 判定縣市是否合法
    clear_user_state, # 清空狀態
    save_default_city # 儲存到雲端資料庫
    
)

from weather_today.today_handler import reply_today_weather_of_city
from weather_current.current_handler import reply_current_weather_of_city
from weather_forecast.forecast_handler import reply_forecast_weather_of_city

from outfit_suggestion.outfit_responses import reply_outfit_weather_of_city

logger = logging.getLogger(__name__)

# --- 所有處理縣市輸入的通用函式 ---
def _process_city_input(api: ApiClient, event: MessageEvent, handler_function) -> bool:
    """
    這個函式的職責是擷取使用者輸入的縣市名稱，進行格式化與有效性驗證。
    如果縣市有效，則呼叫傳入的特定處理函式 (handler_function) 來執行後續業務邏輯，並在完成後清除使用者狀態。若縣市無效，則會回覆提示訊息。
    """
    user_id = event.source.user_id
    reply_token = event.reply_token
    user_input_city = event.message.text.strip()
    normalized_city = normalize_city_name(user_input_city)

    # 處理流程：驗證縣市是否有效
    if is_valid_city(normalized_city):
        # 如果縣市有效，呼叫傳入的特定函式處理，並清除使用者狀態
        handler_function(api, reply_token, user_id, normalized_city)
        clear_user_state(user_id) # 清除使用者狀態
        logger.info(f"用戶 {user_id} 查詢 {normalized_city}，狀態已清除。")
        return True # 處理完畢，返回 True
    else:
        # 如果縣市無效，則回覆錯誤訊息並告知使用者正確格式
        send_line_reply_message(api, reply_token, [TextMessage(text="請輸入有效的台灣縣市名稱，例如：台中市 或 台北市")])
        logger.info(f"用戶 {user_id} 輸入無效城市: {user_input_city}，提示用戶重新輸入。")
        return False # 允許整個訊息路由器繼續運作，這讓使用者可以重新輸入縣市名稱

# --- 處理使用者首次設定預設城市的輸入 ---
# follow.py 負責開始流程，這個函式負責接收並完成流程
def handle_awaiting_default_city_input(api: ApiClient, event: MessageEvent) -> bool:
    """
    這個函式與一般的查詢不同，它的目的是將使用者輸入的縣市儲存起來，而不是立即回覆天氣資訊。
    """
    user_id = event.source.user_id
    reply_token = event.reply_token
    user_input_city = event.message.text.strip()
    normalized_city = normalize_city_name(user_input_city)

    # 處理流程：驗證縣市並儲存為預設縣市
    if is_valid_city(normalized_city):
        # 首先驗證使用者輸入的縣市是否有效。如果有效，就呼叫 `save_default_city` 函式將其永久儲存
        save_default_city(user_id, normalized_city)
        send_line_reply_message(api, reply_token, [TextMessage(text=f"已將預設城市設定為：{normalized_city}！\n您可以開始查詢天氣了。")])
        clear_user_state(user_id) # 清除使用者狀態
        logger.info(f"已為 {user_id} 設定預設城市：{normalized_city}，狀態已清除。")
        return True # 處理完畢，返回 True
    else:
        send_line_reply_message(api, reply_token, [TextMessage(text="請輸入有效的台灣縣市名稱，例如：台中市 或 台北市")])
        logger.info(f"用戶 {user_id} 輸入無效城市：{user_input_city}，提示用戶重新輸入。")
        return False # 允許整個訊息路由器繼續運作。這使得使用者可以重新輸入縣市名稱
    
# --- 處理今日天氣查詢其他縣市的輸入 ---
def handle_awaiting_today_city_input(api: ApiClient, event: MessageEvent) -> bool:
    """
    透過呼叫通用的 `_process_city_input` 函式來完成處理。
    """
    # 這裡使用 `_process_city_input` 函式，並傳入 `reply_today_weather_of_city` 作為業務邏輯處理函式
    # 這樣做的好處是，程式碼可以非常簡潔，同時重用通用的縣市驗證和狀態清除邏輯
    # reply_today_weather_of_city 在 weather_today/today_handler.py 中實現
    return _process_city_input(api, event, reply_today_weather_of_city)

# --- 處理即時天氣查詢其他縣市的輸入 ---
def handle_awaiting_city_input(api: ApiClient, event: MessageEvent) -> bool:
    """
    透過呼叫通用的 `_process_city_input` 函式來完成處理。
    """
    # 這個區塊的邏輯與處理今日天氣的函式相同，只是它會呼叫 `reply_current_weather_of_city` 來回覆即時天氣
    # reply_current_weather_of_city 在 weather_current/current_handler.py 中實現
    return _process_city_input(api, event, reply_current_weather_of_city)

# --- 處理未來預報查詢其他縣市的輸入 (顯示天數選單) ---
def handle_awaiting_forecast_city_input(api: ApiClient, event: MessageEvent) -> bool:
    """
    這裡會利用 `_process_city_input` 函式來呼叫 `reply_forecast_weather_of_city`。
    此函式呼叫一個能夠顯示天數選單的函式，並將使用者輸入的縣市傳遞過去。
    """
    # reply_forecast_weather_of_city 在 weather_forecast/forecast_handler.py 中實現
    return _process_city_input(api, event, reply_forecast_weather_of_city)
    
# --- 處理穿搭建議查詢其他縣市的輸入 ---
def handle_awaiting_outfit_city_input(api: ApiClient, event: MessageEvent) -> bool:
    """
    此函式將縣市輸入交給通用的 `_process_city_input` 函式處理。
    最終由 `reply_outfit_weather_of_city` 函式來生成並回覆穿搭建議。
    """
    # reply_outfit_weather_of_city 在 outfit_suggestion/outfit_handler.py 中實現
    return _process_city_input(api, event, reply_outfit_weather_of_city)