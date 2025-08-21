# utils/message_builder.py
"""
訊息格式化工具模組，將不同類型的資料（例如純文字或字典）轉換為 LINE Messaging API 所需的訊息物件。
將資料處理與訊息物件的構建過程分離，使程式碼更清晰、更易於維護。
主要功能：
1. 純文字訊息格式化：提供一個函式將 Python 字串轉換為 `TextMessage` 物件。
2. Flex Message 轉換：提供一個函式將 Flex Message 的 JSON/字典格式內容轉換為 `FlexMessage` 物件。
   這個函式內建錯誤處理和降級機制，確保在轉換失敗時，應用程式依然能夠發送一個有效的文字訊息給用戶。
"""
import json
import logging
from typing import Union
from linebot.v3.messaging.models import TextMessage, FlexMessage, FlexContainer

logger = logging.getLogger(__name__)

# --- 將純文字字串轉換為 LINE Bot SDK 中的 TextMessage 物件 ---
def format_text_message(text: str) -> TextMessage:
    """
    一個簡單的包裝器，用於統一處理所有純文字訊息的構建過程。
    """
    return TextMessage(text=text)

# --- 將 Flex Message 的內容字典，轉換為 LINE Bot SDK 可用的 FlexMessage 物件 ---
# 因為目前的 Flex Message 都是 Flex SDK，所以目前這個專案沒用到
def format_flex_message(alt_text: str, flex_content_dict: dict) -> Union[FlexMessage, TextMessage]:
    """
    包含輸入驗證、詳細的日誌記錄和錯誤處理。
    如果轉換過程失敗，會自動回退（fallback）到一個純文字訊息，確保訊息傳送不會失敗。

    Args:
        alt_text (str): Flex Message 的替代文字。
        flex_content_dict (dict): Flex Message 的內容字典 (通常是 bubble)。

    Returns:
        FlexMessage | TextMessage: 轉換後的 FlexMessage 物件，或錯誤時的 TextMessage。
    """
    # 1. 前置檢查：確保輸入的字典是有效的
    # 檢查 `flex_content_dict` 是否為字典且不為空，防止程式在處理無效或空輸入時崩潰，並提供一個錯誤訊息作為回傳
    if not isinstance(flex_content_dict, dict) or not flex_content_dict:
        logger.error("收到的 flex_content_dict 無效或為空，無法創建 FlexMessage。")
        return TextMessage(text=f"抱歉，天氣卡片內容生成失敗。")

    # 2. 輸出日誌：用於開發與除錯
    # 輸出原始字典，方便確認傳入的資料結構
    logger.debug(f"即將傳送給 LINE API 的 Flex Message 內容 (原始字典): {flex_content_dict}")

    # 將字典轉換為 JSON 格式，可以將這段 JSON 複製到 Flex Message 模擬器中，直接預覽訊息效果
    logger.debug(f"JSON 格式的 Flex Message 內容: {json.dumps(flex_content_dict, indent=2, ensure_ascii=False)}")
    
    # 3. 轉換與構建 FlexMessage
    try:
        """
        將字典直接傳遞給 FlexContainer.from_dict()。
        `FlexContainer.from_dict()` 是 LINE SDK 提供的一個方法。
        可以將字典轉換為物件，還會自動驗證字典結構是否符合 Flex Message 的規範。
        """
        flex_container_object = FlexContainer.from_dict(flex_content_dict)
        
        # 將 FlexContainer 物件傳遞給 FlexMessage
        flex_message_object = FlexMessage(
            alt_text=alt_text,
            contents=flex_container_object # contents 參數現在直接接收 FlexContainer 物件
        )
        logger.debug("Flex Message 字典成功轉換為 FlexContainer 物件並創建 FlexMessage。")
        return flex_message_object
    except Exception as e:
        # 4. 錯誤處理：降級至純文字訊息
        # 當轉換過程因任何原因失敗時（例如傳入的字典格式不正確），會捕獲異常並返回一個簡單的 TextMessage，讓程式不會崩潰
        logger.error(f"將 Flex Message 字典轉換為物件失敗 (via FlexContainer.from_dict): {e}", exc_info=True)
        return TextMessage(text=f"抱歉，天氣卡片顯示發生問題。替代文字：{alt_text}")