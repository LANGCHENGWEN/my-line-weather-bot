# typhoon/area_hazard_handler.py
"""
用戶查詢「地區影響預警」請求的業務邏輯核心。
主要職責：
1. 作為協調器：將來自 LINE 的用戶請求與三個核心模組（`api`、`parser`、`flex_message`）串聯起來，形成一個完整的處理流程。
2. 處理業務邏輯：
   (1) 數據獲取與處理：呼叫 `AreaHazardLogic` 類別，該類別負責向 CWA API 發送請求、接收原始數據，並進行解析和過濾。
   (2) 訊息建構：將處理後的數據交給 `create_area_hazard_flex_message` 函式，生成一個美觀的 Flex Message。
3. 錯誤處理與回覆：在任何環節（API 失敗、數據解析失敗、訊息建構失敗）發生錯誤時，都能夠安全的捕獲異常，並向用戶回覆友好的文字訊息，而不是讓程式崩潰或無回應。
"""
import logging
from typing import Optional

from linebot.v3.messaging import MessagingApi
from linebot.v3.messaging.models import TextMessage, FlexMessage
from linebot.v3.webhooks.models import MessageEvent

from config import CWA_API_KEY
from utils.line_common_messaging import send_line_reply_message

from .area_hazard_api import AreaHazardApiClient
from .area_hazard_parser import AreaHazardParser
from .area_hazard_flex_message import create_area_hazard_flex_message

logger = logging.getLogger(__name__)

# --- 處理地區影響預警相關的業務邏輯，協調 API 呼叫、數據解析和訊息格式化 ---
class AreaHazardLogic:
    # --- 初始化 `AreaHazardLogic` 類別 ---
    def __init__(self):
        if not CWA_API_KEY: # 檢查 API 授權碼是否存在
            logger.critical("CWA_API_KEY 未設定。無法初始化地區影響預警邏輯。")
            raise ValueError("CWA_API_KEY 未設定。")
        # 初始化 API 客戶端和解析器
        self.api_client = AreaHazardApiClient(CWA_API_KEY)
        self.parser = AreaHazardParser()

    # --- 獲取並處理地區影響預警數據，返回一個 Flex Message 物件 ---
    def get_area_hazard_flex_message(self) -> Optional[FlexMessage]:
        """ 
        整個地區影響預警功能的邏輯核心。
        將分散在不同模組中的功能串聯起來，並處理每一步可能出現的失敗情況。
        執行順序：
        1. 向 CWA API 請求原始數據。
        2. 將原始數據傳給解析器進行解析和篩選。
        3. 將解析後的數據傳給 Flex Message 建構器來創建最終的訊息。

        Returns:
            Optional[FlexMessage]: 成功時返回 FlexMessage，失敗或無數據時返回 None。
        """
        logger.info("開始獲取全台地區影響預警...")

        # 1. 獲取原始預警數據 (通過 self.api_client 調用)
        raw_data = self.api_client.fetch_area_hazard_raw_data()
        if not raw_data:
            logger.warning("無法獲取地區影響預警原始資料。")
            return None
            
        # 2. 解析原始數據 (通過 self.parser 調用)
        parsed_data = self.parser.parse_area_hazard_data(raw_data)
        if not parsed_data:
            logger.info("目前無任何地區影響預警。")
            return None

        # 3. 生成 Flex Message
        # create_area_hazard_flex_message 預期返回 FlexMessage 物件 (Bubble 或 Carousel)
        flex_bubble_object = create_area_hazard_flex_message(parsed_data)
        if not flex_bubble_object:
            logger.error("create_area_hazard_flex_message 未返回 FlexBubble 或 FlexCarousel 物件。")
            return None
        
        return flex_bubble_object

# --- LINE 事件處理的入口點，專門處理與地區影響預警相關的文字訊息事件 ---
def handle_area_hazard_message(api: MessagingApi, event: MessageEvent) -> bool:
    """
    主要職責：
    1. 從事件中提取用戶 ID、回覆令牌和訊息內容。
    2. 呼叫 `AreaHazardLogic` 類別來獲取最終的 Flex Message 物件。
    3. 根據 `AreaHazardLogic` 的返回值，向用戶回覆 Flex Message 或文字錯誤訊息。
    4. 處理可能在任何環節發生的異常，確保程式不會因為單一錯誤而停止運行。
    """
    user_id = event.source.user_id
    reply_token = event.reply_token
    user_message = event.message.text

    if user_message != "地區影響預警": # 如果訊息不是精確的關鍵字，則交由其他 handler 處理
        return False

    logger.info(f"[AreaHazardHandler] 收到用戶 '{user_id}' 的地區影響預警文字請求：'{user_message}'。")

    try:
        # 實例化 AreaHazardLogic，將所有的數據處理工作交給 `AreaHazardLogic` 類別
        # 這將複雜的業務邏輯與簡單的事件處理分開，讓 `handle_area_hazard_message` 函式只專注於接收事件和發送回覆
        area_hazard_logic = AreaHazardLogic()
    except ValueError as e:
        logger.critical(f"[AreaHazardHandler] 實例化 AreaHazardLogic 失敗: {e}")
        send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，系統配置錯誤，無法提供地區影響預警資訊。請聯繫管理員。")])
        return True

    # 呼叫業務邏輯，獲取最終訊息物件
    flex_message_object = area_hazard_logic.get_area_hazard_flex_message()

    # 將 `area_hazard_logic` 處理後的結果發送給用戶
    if flex_message_object:
        try:
            send_line_reply_message(api, reply_token, [flex_message_object])
            logger.info(f"[TyphoonHandler] 成功回覆用戶 '{user_id}' 地區影響預警 Flex Message。")
            return True # 表示事件已處理
        except Exception as e:
            logger.error(f"[TyphoonHandler] 回覆地區影響預警 Flex Message 失敗: {e}", exc_info=True)
            send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，地區影響預警回覆時發生錯誤，請稍候再試。")])
            return True # 雖然失敗，但也算處理過
    else:
        error_message = TextMessage(text="目前沒有相關的地區影響預警資料。")
        return send_line_reply_message(api, reply_token, [error_message])