# current_handler.py
# 主要處理即時天氣用戶輸入的回覆邏輯
import logging
from linebot.v3.messaging.models import TextMessage, FlexMessage, FlexBubble
from linebot.v3.webhooks.models import MessageEvent

# 從 config 載入設定
from config import CWA_API_KEY

# 載入即時天氣相關功能
from .cwa_current_api import get_cwa_current_data
from .weather_flex_message import build_weather_flex
from .weather_current_parser import parse_current_weather

# 導入用戶數據管理器 (用於獲取用戶預設城市)
from utils.user_data_manager import get_default_city # 確保已導入

# 需要導入這個來將 Flex Message 字典轉換為 FlexMessage 物件
from utils.message_builder import format_flex_message

from utils.text_processing import normalize_city_name

# 載入通用訊息發送功能 (如果新增了 line_common_messaging.py，這裡就從那裡導入)
from utils.line_common_messaging import (
    send_line_reply_message, send_api_error_message
)

logger = logging.getLogger(__name__)

def handle_current_message(messaging_api, event: MessageEvent) -> bool:
    """
    處理即時天氣查詢的核心邏輯。
    如果訊息被處理，則返回 True，否則返回 False。
    """
    user_id = event.source.user_id
    message_text = event.message.text
    reply_token = event.reply_token

    logger.info(f"收到來自用戶 {user_id} 的訊息: {message_text}")

    # 檢查是否包含「即時天氣」關鍵字
    if "即時天氣" in message_text:
        # 處理即時天氣查詢
        logger.info(f"用戶 {user_id} 查詢即時天氣。")

        # --- 變更點：從用戶數據管理器獲取城市，並設定預設值 ---
        user_city = get_default_city(user_id) 
        if not user_city:
            user_city = "臺中市" # 這裡可以設定一個最常用的預設城市
            logger.info(f"用戶 {user_id} 未設定預設城市，使用預設值：{user_city}")
        # --- 變更點結束 ---

        # 🚀 在這裡將 LOCATION_NAME 正規化
        normalized_location_name = normalize_city_name(user_city)

        # 1. 取得原始天氣數據
        current_data = get_cwa_current_data(CWA_API_KEY, normalized_location_name)

        if not current_data:
            logger.error("無法取得中央氣象署即時觀測資料。")
            send_api_error_message(messaging_api, user_id, reply_token, normalized_location_name)
            return True # 即使出錯也表示這個 handler 嘗試處理了

        # 2. 解析並格式化天氣數據 (得到可以直接用於 Flex Message 模板的字典)
        parsed_current_weather = parse_current_weather(current_data, normalized_location_name)
        
        if not parsed_current_weather:
            logger.error(f"無法從取得的即時觀測資料中解析或格式化出 {normalized_location_name} 的天氣資訊。")
            send_api_error_message(messaging_api, user_id, reply_token, normalized_location_name)
            return True # 即使出錯也表示這個 handler 嘗試處理了
        
        # 3. 將格式化後的數據填充到 Flex Message 模板中 (得到 Flex Message 的字典結構)
        # 用你的 builder 產生 Flex JSON
        weather_flex_bubble = build_weather_flex(parsed_current_weather)

        # 檢查 format_current_weather_message 是否返回有效的字典 (而不是錯誤字串)
        if not isinstance(weather_flex_bubble, FlexBubble): # 檢查回傳的類型
            logger.error(f"build_weather_flex 返回了無效的 FlexBubble 物件: {type(weather_flex_bubble)}")
            # 這裡可以選擇發送一個通用的錯誤文字訊息，而不是嘗試再構建一次 FlexMessage
            error_message_obj = TextMessage(text=f"抱歉，無法顯示 {normalized_location_name} 的天氣資訊卡片。請稍候再試。")
            send_line_reply_message(messaging_api, reply_token, [error_message_obj])
            return True
        
        # 4. 將 Flex Message 字典轉換為 Line Bot SDK 的 FlexMessage 物件
        # 使用 line_common_messaging 中的 format_flex_message 函數
        flex_msg_to_send = FlexMessage(
            alt_text=f"{normalized_location_name} 即時天氣",
            contents=weather_flex_bubble # 直接傳入 FlexBubble 物件
        )

        # 5. 發送回覆訊息 (傳入 Line Bot SDK 的 Message 物件列表)
        # line_flex_message_object 已經是一個 FlexMessage 物件，將其放入列表中
        send_line_reply_message(messaging_api, reply_token, [flex_msg_to_send])
        return True # 訊息已處理
    
    return False # 這個 handler 沒有處理這個訊息

# 在 current_handler.py 最下方加一個 util
def reply_current_weather_of_city(api, reply_token: str, city_name: str) -> None:
    """
    直接根據 city_name 抓資料、組 Flex、回覆。
    用在「查詢其他縣市」或任何想動態查城市的地方。
    """
    # 🚀 在這裡正規化傳入的 city_name
    normalized_city_name = normalize_city_name(city_name)

    # 1. 取資料
    raw = get_cwa_current_data(CWA_API_KEY, normalized_city_name)
    if not raw:
        send_api_error_message(api, None, reply_token, normalized_city_name)
        return

    # 2. 解析
    parsed = parse_current_weather(raw, normalized_city_name)
    if not parsed:
        send_api_error_message(api, None, reply_token, normalized_city_name)
        return

    # 3. build flex json → FlexMessage
    weather_flex_bubble = build_weather_flex(parsed)

    if not isinstance(weather_flex_bubble, FlexBubble): # 檢查回傳的類型
            logger.error(f"reply_current_weather_of_city 中 build_weather_flex 返回了無效的 FlexBubble 物件: {type(weather_flex_bubble)}")
            # 這裡可以選擇發送一個通用的錯誤文字訊息，而不是嘗試再構建一次 FlexMessage
            error_message_obj = TextMessage(text=f"抱歉，無法顯示 {normalized_city_name} 的天氣資訊卡片。請稍候再試。")
            send_line_reply_message(api, reply_token, [error_message_obj])
            return True

    flex_msg_to_send = FlexMessage(
            alt_text=f"{normalized_city_name} 即時天氣",
            contents=weather_flex_bubble # 直接傳入 FlexBubble 物件
        )

    # 4. 回覆
    send_line_reply_message(api, reply_token, [flex_msg_to_send])


    '''
        # 5. 發送回覆訊息 (傳入 Line Bot SDK 的 Message 物件)
        send_line_reply_message(messaging_api, reply_token, line_flex_message_object)

        return True # 訊息已處理
    '''
    
    return False # 這個 handler 沒有處理這個訊息

logger.info("即時天氣處理器已載入。")