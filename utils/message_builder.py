# message_builder.py
# 負責格式化通用訊息
import json
import logging
from typing import Union
from linebot.v3.messaging.models import TextMessage, FlexMessage, FlexContainer
# from linebot.models.flex_message import BubbleContainer
# FlexContainer

logger = logging.getLogger(__name__)

# --- 訊息格式化工具函數 ---
def format_text_message(text: str) -> TextMessage:
    """
    將純文字字串包裝成 Line TextMessage 物件。
    """
    return TextMessage(text=text)

def format_flex_message(alt_text: str, flex_content_dict: dict) -> Union[FlexMessage, TextMessage]:
    """
    將 Flex Message 的字典內容轉換為 Line Bot SDK 的 FlexMessage 物件。
    使用 FlexContainer 進行轉換，提供更好的驗證。
    如果轉換失敗，則返回一個 TextMessage 作為降級處理。

    Args:
        alt_text (str): Flex Message 的替代文字。
        flex_content_dict (dict): Flex Message 的內容字典 (通常是 bubble)。

    Returns:
        FlexMessage | TextMessage: 轉換後的 FlexMessage 物件，或錯誤時的 TextMessage。
    """
    if not isinstance(flex_content_dict, dict) or not flex_content_dict:
        logger.error("收到的 flex_content_dict 無效或為空，無法創建 FlexMessage。")
        return TextMessage(text=f"抱歉，天氣卡片內容生成失敗。")

    logger.debug(f"即將傳送給 LINE API 的 Flex Message 內容 (原始字典): {flex_content_dict}") # <-- ADD THIS LINE
    # 可以選擇性地輸出為 JSON 格式，以便複製到模擬器中測試
    logger.debug(f"JSON 格式的 Flex Message 內容: {json.dumps(flex_content_dict, indent=2, ensure_ascii=False)}") # <-- ADD THIS LINE
    
    try:
        # 將字典直接傳遞給 FlexContainer.from_dict()
        # FlexContainer 會自動驗證並構建其內部組件
        flex_container_object = FlexContainer.from_dict(flex_content_dict)
        
        # 然後將 FlexContainer 物件傳遞給 FlexMessage
        flex_message_object = FlexMessage(
            alt_text=alt_text,
            contents=flex_container_object # contents 參數現在直接接收 FlexContainer 物件
        )
        logger.debug("Flex Message 字典成功轉換為 FlexContainer 物件並創建 FlexMessage。")
        return flex_message_object
    except Exception as e:
        logger.error(f"將 Flex Message 字典轉換為物件失敗 (via FlexContainer.from_dict): {e}", exc_info=True)
        # 降級處理：返回一個普通的文本訊息
        return TextMessage(text=f"抱歉，天氣卡片顯示發生問題。替代文字：{alt_text}")