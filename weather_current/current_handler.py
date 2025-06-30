# current_handler.py
# 主要處理即時天氣用戶輸入的回覆邏輯
import logging

from linebot.v3.webhooks.models import MessageEvent, TextMessageContent
from linebot.v3.messaging.models import TextMessage, FlexMessage
# from linebot.v3.messaging.models import TextMessage

# 從 config 載入設定
from config import CWA_API_KEY, LOCATION_NAME, setup_logging

# 載入即時天氣相關功能
from .cwa_current_api import get_cwa_current_data
from .weather_current_parser import parse_current_weather
from .line_current_messaging import format_current_weather_message # 只導入 current 的格式化

# 載入通用訊息發送功能 (如果新增了 line_common_messaging.py，這裡就從那裡導入)
from utils.line_common_messaging import (
    send_line_reply_message,
    send_api_error_message
)

from utils.message_builder import ( # 假設您新增了此檔案並同意這樣拆分
    format_flex_message, # 需要導入這個來將 Flex Message 字典轉換為 FlexMessage 物件
    format_text_message # 如果 send_api_error_message 不夠用，可能需要這個
)

logger = setup_logging(__name__)

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

        # 1. 取得原始天氣數據
        current_data = get_cwa_current_data(CWA_API_KEY, LOCATION_NAME)

        if not current_data:
            logger.error("無法取得中央氣象署即時觀測資料。")
            send_api_error_message(messaging_api, user_id, reply_token, LOCATION_NAME)
            return True # 即使出錯也表示這個 handler 嘗試處理了

        # 2. 解析並格式化天氣數據 (得到可以直接用於 Flex Message 模板的字典)
        parsed_and_formatted_weather = parse_current_weather(current_data, LOCATION_NAME)

        if not parsed_and_formatted_weather:
            logger.error(f"無法從取得的即時觀測資料中解析或格式化出 {LOCATION_NAME} 的天氣資訊。")
            send_api_error_message(messaging_api, user_id, reply_token, LOCATION_NAME)
            return True # 即使出錯也表示這個 handler 嘗試處理了
        
        # 3. 將格式化後的數據填充到 Flex Message 模板中 (得到 Flex Message 的字典結構)
        flex_message_dict = format_current_weather_message(parsed_and_formatted_weather, LOCATION_NAME)

        # 檢查 format_current_weather_message 是否返回有效的字典 (而不是錯誤字串)
        if not flex_message_dict: # 如果 format_current_weather_message 返回空字典或 None
            logger.error(f"格式化即時天氣 Flex Message 失敗，返回錯誤訊息給用戶。")
            # 這裡可以選擇發送一個通用的錯誤文字訊息
            error_message_obj = TextMessage(text=f"抱歉，無法顯示 {LOCATION_NAME} 的天氣資訊卡片。請稍後再試。")
            send_line_reply_message(messaging_api, reply_token, [error_message_obj])
            return True
        
        # 4. 將 Flex Message 字典轉換為 Line Bot SDK 的 FlexMessage 物件
        # 使用 line_common_messaging 中的 format_flex_message 函數
        line_flex_message_object = format_flex_message(
            alt_text=f"{LOCATION_NAME} 即時天氣資訊", # 替代文字，當 Flex Message 無法顯示時使用
            flex_content_dict=flex_message_dict
        )

        # 額外檢查：format_flex_message 也可能返回 TextMessage (降級處理)
        if isinstance(line_flex_message_object, TextMessage): # 如果 format_flex_message 發生錯誤並返回 TextMessage
            send_line_reply_message(messaging_api, reply_token, [line_flex_message_object])
            return True

        # 5. 發送回覆訊息 (傳入 Line Bot SDK 的 Message 物件列表)
        # line_flex_message_object 已經是一個 FlexMessage 物件，將其放入列表中
        send_line_reply_message(messaging_api, reply_token, [line_flex_message_object])
        
        return True # 訊息已處理

    '''
        # 5. 發送回覆訊息 (傳入 Line Bot SDK 的 Message 物件)
        send_line_reply_message(messaging_api, reply_token, line_flex_message_object)

        return True # 訊息已處理
    '''
    
    return False # 這個 handler 沒有處理這個訊息

logger.info("即時天氣處理器已載入。")