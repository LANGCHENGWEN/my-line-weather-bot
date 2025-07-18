# current_handler.py
# 主要處理即時天氣用戶輸入的回覆邏輯
import logging
from linebot.v3.messaging.models import TextMessage
from linebot.v3.webhooks.models import MessageEvent

# 從 config 載入設定
from config import CWA_API_KEY, LOCATION_NAME

# 載入即時天氣相關功能
from .cwa_current_api import get_cwa_current_data
from .weather_current_parser import parse_current_weather
from .line_current_messaging import format_current_weather_message # 只導入 current 的格式化
from .weather_flex_message import build_weather_flex

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

        # 🚀 在這裡將 LOCATION_NAME 正規化
        normalized_location_name = normalize_city_name(LOCATION_NAME)

        # 1. 取得原始天氣數據
        current_data = get_cwa_current_data(CWA_API_KEY, normalized_location_name)

        if not current_data:
            logger.error("無法取得中央氣象署即時觀測資料。")
            send_api_error_message(messaging_api, user_id, reply_token, normalized_location_name)
            return True # 即使出錯也表示這個 handler 嘗試處理了

        # 2. 解析並格式化天氣數據 (得到可以直接用於 Flex Message 模板的字典)
        weather_dict = parse_current_weather(current_data, normalized_location_name)

        if not weather_dict:
            logger.error(f"無法從取得的即時觀測資料中解析或格式化出 {normalized_location_name} 的天氣資訊。")
            send_api_error_message(messaging_api, user_id, reply_token, normalized_location_name)
            return True # 即使出錯也表示這個 handler 嘗試處理了
        
        # 3. 將格式化後的數據填充到 Flex Message 模板中 (得到 Flex Message 的字典結構)
        # 用你的 builder 產生 Flex JSON
        flex_json = build_weather_flex(weather_dict)

        # 檢查 format_current_weather_message 是否返回有效的字典 (而不是錯誤字串)
        if not flex_json: # 如果 format_current_weather_message 返回空字典或 None
            logger.error(f"格式化即時天氣 Flex Message 失敗，返回錯誤訊息給用戶。")
            # 這裡可以選擇發送一個通用的錯誤文字訊息
            error_message_obj = TextMessage(text=f"抱歉，無法顯示 {normalized_location_name} 的天氣資訊卡片。請稍後再試。")
            send_line_reply_message(messaging_api, reply_token, [error_message_obj])
            return True
        
        # 4. 將 Flex Message 字典轉換為 Line Bot SDK 的 FlexMessage 物件
        # 使用 line_common_messaging 中的 format_flex_message 函數
        flex_msg = format_flex_message(f"{normalized_location_name} 即時天氣", flex_json)

        # 額外檢查：format_flex_message 也可能返回 TextMessage (降級處理)
        if isinstance(flex_msg, TextMessage): # 如果 format_flex_message 發生錯誤並返回 TextMessage
            send_line_reply_message(messaging_api, reply_token, [flex_msg])
            return True

        # 5. 發送回覆訊息 (傳入 Line Bot SDK 的 Message 物件列表)
        # line_flex_message_object 已經是一個 FlexMessage 物件，將其放入列表中
        send_line_reply_message(messaging_api, reply_token, flex_msg)
        return True # 訊息已處理
    
    return False # 這個 handler 沒有處理這個訊息
    
# 在 current_handler.py 最下方加一個 util
def reply_weather_of_city(api, reply_token: str, city_name: str) -> None:
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
    flex_json = build_weather_flex(parsed)
    flex_msg  = format_flex_message(f"{normalized_city_name} 即時天氣", flex_json)

    # 4. 回覆
    send_line_reply_message(api, reply_token, flex_msg)


    '''
        # 5. 發送回覆訊息 (傳入 Line Bot SDK 的 Message 物件)
        send_line_reply_message(messaging_api, reply_token, line_flex_message_object)

        return True # 訊息已處理
    '''
    
    return False # 這個 handler 沒有處理這個訊息

logger.info("即時天氣處理器已載入。")