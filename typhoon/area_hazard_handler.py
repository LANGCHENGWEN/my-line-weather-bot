# typhoon/area_hazard_handler.py
import re
import logging
from typing import Any, Dict, List, Union, Optional

from linebot.v3.messaging import MessagingApi
from linebot.v3.messaging.models import TextMessage, FlexMessage, FlexBubble, Message
from linebot.v3.webhooks.models import MessageEvent

from config import CWA_API_KEY # 從 config.py 導入 API Key
# 假設這些工具函式存在於你的 utils 資料夾中
from utils.line_common_messaging import send_line_reply_message

from .area_hazard_api import AreaHazardApiClient
from .area_hazard_parser import AreaHazardParser
from .area_hazard_flex_message import create_area_hazard_flex_message

logger = logging.getLogger(__name__)

# 輔助函式：用於生成簡單的文字訊息
def create_text_message(text: str) -> TextMessage:
    return TextMessage(text=text)

class AreaHazardLogic:
    """
    處理地區影響預警相關的業務邏輯，協調 API 呼叫、數據解析和訊息格式化。
    """
    def __init__(self):
        if not CWA_API_KEY:
            logger.critical("CWA_API_KEY 未設定。無法初始化地區影響預警邏輯。")
            raise ValueError("CWA_API_KEY 未設定。")
        self.api_client = AreaHazardApiClient(CWA_API_KEY)
        self.parser = AreaHazardParser()
        # area_hazard_api.py 中的 get_area_hazard_warnings_from_cwa 是函式，所以這裡不需要實例化客戶端
        # self.api_client = AreaHazardApiClient(CWA_API_KEY) # 如果 get_area_hazard_warnings_from_cwa 是一個類別方法，這裡才需要實例化

    def get_area_hazard_flex_message(self, target_city: Optional[str] = None) -> Optional[FlexMessage]:
        """
        獲取並處理地區影響預警數據，返回一個 Flex Message 物件。
        """
        logger.info(f"開始獲取 {target_city if target_city else '所有地區'} 的地區影響預警...")

        # 1. 獲取原始預警數據 (現在通過 self.api_client 調用)
        raw_data = self.api_client.fetch_area_hazard_raw_data()

        if not raw_data:
            logger.warning("無法獲取地區影響預警原始資料。")
            return None
            

        # 2. 解析原始數據
        parsed_data = self.parser.parse_area_hazard_data(raw_data, target_city=target_city)
        
        if not parsed_data:
            logger.info(f"無 {target_city if target_city else '全台'} 相關地區影響預警。")
            return None

        # 3. 生成 Flex Message
        # build_area_hazard_flex_message 預期返回 FlexMessage 物件 (可以是 Bubble 或 Carousel)
        flex_bubble_object = create_area_hazard_flex_message(parsed_data, target_city=target_city)
        
        if not flex_bubble_object:
            logger.error("build_area_hazard_flex_message 未返回 FlexBubble 或 FlexCarousel 物件。")
            return None
        
        return flex_bubble_object

# --- LINE 事件處理入口函式 ---
def handle_area_hazard_message(api: MessagingApi, event: MessageEvent) -> bool:
    """
    
    """
    user_id = event.source.user_id
    reply_token = event.reply_token
    user_message = event.message.text

    logger.info(f"[AreaHazardHandler] 收到用戶 '{user_id}' 的地區影響預警文字請求：'{user_message}'。")

    try:
        area_hazard_logic = AreaHazardLogic() # 在這裡初始化 AreaHazardLogic
    except ValueError as e:
        logger.critical(f"[AreaHazardHandler] 初始化 AreaHazardLogic 失敗: {e}")
        send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，系統配置錯誤，無法提供地區影響預警資訊。請聯繫管理員。")])
        return True

    target_city = None
    if " " in user_message and user_message.startswith("地區影響預警"):
        parts = user_message.split(" ", 1)
        if len(parts) > 1:
            target_city = parts[1].strip()

    flex_message_object = area_hazard_logic.get_area_hazard_flex_message(target_city=target_city)

    if flex_message_object:
        try:
            send_line_reply_message(api, reply_token, [flex_message_object])
            logger.info(f"[TyphoonHandler] 成功回覆用戶 '{user_id}' 地區影響預警 Flex Message。")
            return True # 表示事件已處理
        except Exception as e:
            logger.error(f"[TyphoonHandler] 回覆地區影響預警 Flex Message 失敗: {e}", exc_info=True)
            # 如果 Flex Message 發送失敗，可以考慮發送一個 TextMessage 作為備用
            send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，地區影響預警回覆時發生錯誤，請稍候再試。")])
            return True # 雖然失敗，但也算處理過
    else:
        city_display_text = f" {target_city}" if target_city else ""
        error_message = create_text_message(f"目前沒有{city_display_text}相關的地區影響預警資料。")
        return send_line_reply_message(api, reply_token, [error_message])

    

    # 調用非同步方法獲取 Flex Message
    flex_message_object = area_hazard_logic.get_area_hazard_flex_message(target_city=target_city)

    if flex_message_object:
        # 如果成功獲取到 Flex Message 物件，則回覆它
        try:
            send_line_reply_message(api, reply_token, [flex_message_object])
            logger.info(f"[AreaHazardHandler] 成功回覆用戶 '{user_id}' 地區影響預警 Flex Message。")
            return True # 表示事件已處理
        except Exception as e:
            logger.error(f"[AreaHazardHandler] 回覆地區影響預警 Flex Message 失敗: {e}", exc_info=True)
            # 如果 Flex Message 發送失敗，可以考慮發送一個 TextMessage 作為備用
            send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，地區影響預警回覆時發生錯誤，請稍候再試。")])
            return True # 雖然失敗，但也算處理過
    else:
        # 如果無法生成 Flex Message (例如 API 失敗、數據解析失敗或沒有預警)
        send_line_reply_message(api, reply_token, [TextMessage(text=f"目前沒有相關的地區影響預警。")])
        logger.warning(f"[AreaHazardHandler] 無法為用戶 '{user_id}' 取得或生成地區影響預警資訊。")
        return True # 表示事件已處理