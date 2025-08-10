# current_handler.py
# 主要處理即時天氣用戶輸入的回覆邏輯
import logging
from linebot.v3.messaging import ApiClient
from linebot.v3.messaging.models import TextMessage, FlexMessage, FlexBubble
from linebot.v3.webhooks.models import MessageEvent

# 從 config 載入設定
from config import CWA_API_KEY

# 載入即時天氣相關功能
from .cwa_current_api import get_cwa_current_data
from .weather_flex_message import build_weather_flex
from .weather_current_parser import parse_current_weather

# 導入用戶數據管理器 (用於獲取用戶預設城市)
from utils.firestore_manager import get_default_city # 確保已導入

# 需要導入這個來將 Flex Message 字典轉換為 FlexMessage 物件
from utils.message_builder import format_flex_message

from utils.text_processing import normalize_city_name

# 載入通用訊息發送功能 (如果新增了 line_common_messaging.py，這裡就從那裡導入)
from utils.line_common_messaging import (
    send_line_reply_message, send_api_error_message
)

logger = logging.getLogger(__name__)

# --- 新增共用函式 ---
def fetch_and_parse_weather_data(city_name: str) -> dict | None:
    """
    通用函式：獲取並解析指定城市的即時天氣資料。
    如果成功，回傳解析後的字典；如果失敗，回傳 None。
    """
    # 🚀 在這裡將 LOCATION_NAME 正規化
    normalized_city_name = normalize_city_name(city_name)

    # 1. 取得原始天氣數據
    current_data = get_cwa_current_data(CWA_API_KEY, normalized_city_name)
    if not current_data:
        logger.error(f"無法取得 {normalized_city_name} 的中央氣象署即時觀測資料。")
        return None
    
    # 2. 解析並格式化天氣數據 (得到可以直接用於 Flex Message 模板的字典)
    parsed_current_weather = parse_current_weather(current_data, normalized_city_name)
    if not parsed_current_weather:
        logger.error(f"無法解析或格式化 {normalized_city_name} 的即時天氣資訊。")
        return None
    
    return parsed_current_weather

# 新增一個核心函式來處理所有邏輯
def current_weather_reply_by_city(messaging_api: ApiClient, reply_token: str, city_name: str) -> None:
    """
    核心函式：根據城市名稱查詢天氣並發送 Flex 訊息回覆。
    """
    # 使用新的共用函式來獲取解析後的數據
    parsed_data = fetch_and_parse_weather_data(city_name)
    if not parsed_data:
        # 如果共用函式回傳 None，表示發生錯誤，發送錯誤訊息
        send_api_error_message(messaging_api, None, reply_token, city_name)
        return
    
    # 3. 將格式化後的數據填充到 Flex Message 模板中
    weather_flex_bubble = build_weather_flex(parsed_data)
    if not isinstance(weather_flex_bubble, FlexBubble): # 檢查回傳的類型
        logger.error(f"build_weather_flex 返回了無效的 FlexBubble 物件: {type(weather_flex_bubble)}")
        # 這裡可以選擇發送一個通用的錯誤文字訊息，而不是嘗試再構建一次 FlexMessage
        error_message_obj = TextMessage(text=f"抱歉，無法顯示 {city_name} 的天氣資訊卡片。請稍候再試。")
        send_line_reply_message(messaging_api, reply_token, [error_message_obj])
        return True
    
    # 4. 發送回覆訊息
    flex_msg_to_send = FlexMessage(
        alt_text=f"{city_name} 即時天氣",
        contents=weather_flex_bubble # 直接傳入 FlexBubble 物件
    )
    # line_flex_message_object 已經是一個 FlexMessage 物件，將其放入列表中
    send_line_reply_message(messaging_api, reply_token, [flex_msg_to_send])

def handle_current_message(messaging_api: ApiClient, event: MessageEvent) -> bool:
    user_id = event.source.user_id
    message_text = event.message.text
    reply_token = event.reply_token

    logger.info(f"收到來自用戶 {user_id} 的訊息: {message_text}")

    # 檢查是否包含「即時天氣」關鍵字
    if "即時天氣" in message_text:
        # 處理即時天氣查詢
        logger.info(f"用戶 {user_id} 查詢即時天氣。")
        # --- 變更點：從用戶數據管理器獲取城市，並設定預設值 ---
        user_city = get_default_city(user_id) or "臺中市"

        # 呼叫新的核心函式來處理回覆邏輯
        current_weather_reply_by_city(messaging_api, reply_token, user_city)
        return True

    return False # 這個 handler 沒有處理這個訊息

# 在 current_handler.py 最下方加一個 util
def reply_current_weather_of_city(api: ApiClient, reply_token: str, user_id: str, city_name: str) -> None:
    # 呼叫新的核心函式來處理回覆邏輯
    current_weather_reply_by_city(api, reply_token, city_name)

logger.info("即時天氣處理器已載入。")