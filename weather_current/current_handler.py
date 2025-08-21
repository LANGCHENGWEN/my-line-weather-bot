# weather_current/current_handler.py
"""
訊息處理器（handler），處理與「即時天氣」查詢相關的用戶請求。
主要職責：
1. 識別意圖：檢查用戶輸入的訊息是否包含「即時天氣」關鍵字。
2. 數據獲取與處理：從用戶數據中讀取預設城市，並呼叫外部 API 獲取即時天氣資料，然後進行解析和格式化。
3. 介面生成與回覆：將處理好的天氣資料填充到 Flex Message 模板中，並將生成的訊息物件回覆給用戶。
4. 錯誤處理：在任何環節（如 API 呼叫失敗、數據解析失敗）發生錯誤時，提供適當的錯誤訊息回覆用戶。
"""
import logging
from linebot.v3.messaging import ApiClient
from linebot.v3.messaging.models import TextMessage, FlexMessage, FlexBubble
from linebot.v3.webhooks.models import MessageEvent

from config import CWA_API_KEY

from utils.firestore_manager import get_default_city # 導入用戶數據管理器 (用於獲取用戶預設城市)
from utils.text_processing import normalize_city_name
from utils.line_common_messaging import send_line_reply_message, send_api_error_message

# 導入即時天氣相關功能
from .cwa_current_api import get_cwa_current_data
from .weather_flex_message import build_weather_flex
from .weather_current_parser import parse_current_weather

logger = logging.getLogger(__name__)

# --- 共用函式：獲取並解析指定城市的即時天氣資料 ---
def fetch_and_parse_weather_data(city_name: str) -> dict | None:
    """
    提供一個單一的入口點，讓其他函式可以取得格式化後的天氣數據，無需關心底層的 API 呼叫細節。
    如果成功，回傳解析後的字典；如果失敗，回傳 None。
    """
    # 將 city_name 正規化
    # `normalize_city_name` 函式將「台」和「臺」不同寫法統一，確保無論用戶輸入何種寫法，後續的 API 查詢都能使用標準化的城市名稱，提高成功率
    normalized_city_name = normalize_city_name(city_name)

    # 1. 取得原始天氣數據
    current_data = get_cwa_current_data(CWA_API_KEY, normalized_city_name)
    if not current_data:
        logger.error(f"無法取得 {normalized_city_name} 的中央氣象署即時觀測資料。")
        return None # 如果失敗，直接返回 `None`，避免執行不必要的後續步驟
    
    # 2. 解析並格式化天氣數據 (得到可直接用於 Flex Message 模板的字典)
    parsed_current_weather = parse_current_weather(current_data, normalized_city_name)
    if not parsed_current_weather:
        logger.error(f"無法解析或格式化 {normalized_city_name} 的即時天氣資訊。")
        return None
    
    return parsed_current_weather

# --- 核心函式：根據指定的城市名稱，完成從數據獲取到訊息回覆的整個流程 ---
def current_weather_reply_by_city(messaging_api: ApiClient, reply_token: str, city_name: str) -> None:
    """
    協調 `fetch_and_parse_weather_data` 和 Flex Message 的構建與發送。
    """
    # 1. 獲取並解析數據
    # 直接呼叫上面定義的共用函式，避免重複的 API 呼叫和解析邏輯
    parsed_data = fetch_and_parse_weather_data(city_name)
    if not parsed_data:
        # 如果 `fetch_and_parse_weather_data` 返回 `None`，表示發生錯誤，發送錯誤訊息
        send_api_error_message(messaging_api, None, reply_token, city_name)
        return
    
    # 2. 將格式化後的數據填充到 Flex Message 模板中
    weather_flex_bubble = build_weather_flex(parsed_data)
    if not isinstance(weather_flex_bubble, FlexBubble): # 檢查回傳的類型
        logger.error(f"build_weather_flex 返回了無效的 FlexBubble 物件: {type(weather_flex_bubble)}")
        # 發送一個通用的錯誤文字訊息，而不是嘗試再構建一次 FlexMessage
        error_message_obj = TextMessage(text=f"抱歉，無法顯示 {city_name} 的天氣資訊卡片。請稍候再試。")
        send_line_reply_message(messaging_api, reply_token, [error_message_obj])
        return True
    
    # 3. 發送回覆訊息
    # 將構建好的 `FlexBubble` 包裝成 LINE API 所需的 `FlexMessage` 物件
    flex_msg_to_send = FlexMessage(
        alt_text=f"{city_name} 即時天氣",
        contents=weather_flex_bubble
    )
    send_line_reply_message(messaging_api, reply_token, [flex_msg_to_send])

# --- 主訊息處理器 ---
def handle_current_message(messaging_api: ApiClient, event: MessageEvent) -> bool:
    """
    由 `text_router.py` 呼叫。
    判斷收到的訊息是否與即時天氣查詢相關；如果是，則觸發相應的處理流程。
    """
    user_id = event.source.user_id
    message_text = event.message.text
    reply_token = event.reply_token

    logger.info(f"收到來自用戶 {user_id} 的訊息: {message_text}")

    # 檢查是否包含「即時天氣」關鍵字
    if "即時天氣" in message_text:
        logger.info(f"用戶 {user_id} 查詢即時天氣。")
        # 獲取用戶預設城市，並設定預設值
        # 即使新用戶沒有設定預設城市，也能得到一個有意義的回覆，而不是錯誤訊息
        user_city = get_default_city(user_id) or "臺中市"

        # 呼叫核心函式處理回覆邏輯
        current_weather_reply_by_city(messaging_api, reply_token, user_city)
        return True

    return False

# --- 當用戶想查詢即時天氣的其他縣市時，直接呼叫這個函式 ---
def reply_current_weather_of_city(api: ApiClient, reply_token: str, user_id: str, city_name: str) -> None:
    # 呼叫核心函式處理回覆邏輯
    current_weather_reply_by_city(api, reply_token, city_name)

logger.info("即時天氣處理器已載入。")