# solar_terms/solar_terms_handler.py
"""
LINE Bot 處理「節氣小知識」查詢請求的控制器。
主要職責：
1. 協調模組：將來自 `solar_terms_calculator`（負責計算和獲取節氣數據）和 `solar_terms_flex_builder`（負責將數據轉為 Flex Message UI）的邏輯串聯起來。
2. 處理用戶請求：當用戶觸發節氣查詢的事件時，`handle_solar_term_query` 函式會被調用，呼叫計算模組來獲取當前節氣的詳細資訊。
3. 生成並回覆訊息：利用獲取的節氣資訊，調用建構器模組生成一個美觀的 Flex Message，並發送給用戶。
4. 錯誤處理：在處理過程中，如果發生任何錯誤（例如無法獲取數據或生成訊息失敗），會捕獲異常並向用戶回覆一個友好的錯誤提示訊息。

將「處理請求」、「獲取數據」和「生成 UI」這三個核心職責分開，使得每個模組都專注於自己的任務，提高程式碼的可讀性和可維護性。
"""
import logging
from linebot.v3.messaging.models import TextMessage, FlexMessage
from utils.line_common_messaging import send_line_reply_message
from .solar_terms_flex_builder import build_solar_term_flex_message
from .solar_terms_calculator import get_current_solar_term_info_for_display

logger = logging.getLogger(__name__)

# --- 公共函式：獲取節氣資訊並建構 Flex Message ---
def get_solar_term_flex_message(solar_term_data):
    """
    接收一個包含節氣數據的字典，呼叫 `build_solar_term_flex_message` 函式來建立一個 Flex Message 物件。
    提供一個公共介面，讓其他模組（例如推播排程器）也能夠直接使用相同的邏輯來生成節氣訊息，避免程式碼重複。
    包含錯誤處理機制，確保在建構失敗時能安全的返回 `None`。

    Args: 
        solar_term_data (dict): 包含節氣詳細資訊的字典。

    Returns:
        FlexMessage | None: 成功時返回 FlexMessage 物件，失敗時返回 None。
    """
    if not solar_term_data:
        return None
    
    try:
        # 直接呼叫建構器，返回完整的 FlexMessage 物件
        flex_message_to_send = build_solar_term_flex_message(solar_term_data)
        if not isinstance(flex_message_to_send, FlexMessage): # 檢查 build_solar_term_flex_message 是否返回了有效的 FlexBubble
            logger.error(f"build_solar_term_flex_message 返回了無效的物件，類型: {type(flex_message_to_send)}")
            return None
        return flex_message_to_send
    except Exception as e:
        logger.exception(f"建構節氣 Flex Message 時發生錯誤: {e}")
        return None

# --- 處理用戶手動查詢「節氣小知識」的請求 ---
def handle_solar_term_query(api, event):
    """
    執行流程：
    1. 呼叫 `get_current_solar_term_info_for_display` 函式來計算當前節氣。
    2. 呼叫 `get_solar_term_flex_message` 公共函式來生成 Flex Message。
    3. 根據生成結果，將訊息（Flex Message 或錯誤文字）發送給用戶。
    4. 進行全面的錯誤處理，以應對所有可能發生的異常。
    """
    user_id = event.source.user_id
    reply_token = event.reply_token

    logger.info(f"[SolarTermsHandler] 收到節氣查詢請求。用戶: {user_id}")
    
    try:
        # 1. 獲取當前時間的節氣資訊
        # 使用 get_current_solar_term_info_for_display 來處理用戶查詢，找出最近一個已經發生的節氣作為「當前」節氣
        solar_term_data = get_current_solar_term_info_for_display()

        # 2. 呼叫公共函式建構 Flex Message
        flex_message_to_send = get_solar_term_flex_message(solar_term_data)

        if flex_message_to_send:
            # 3. 發送 FlexMessage
            # 因為 build_solar_term_flex_message 已經返回一個完整的 FlexMessage，所以這裡只需要將它包裝在一個列表中即可
            send_line_reply_message(api, reply_token, [flex_message_to_send])
            logger.info(f"[SolarTermsHandler] 成功回覆 {solar_term_data['name']} 節氣小知識 (Flex Message)。")
            return True # 永遠返回 True，表示事件已處理
        else: # 如果 Flex Message 建構失敗，回覆文字訊息
            send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，目前無法取得節氣資訊，請稍候再試。")])
            logger.warning("[SolarTermsHandler] 未能取得節氣資料或卡片生成失敗。")
            return True

    # 4. 處理所有未預期的錯誤，並回覆錯誤訊息
    except Exception as e:
        logger.exception(f"[SolarTermsHandler] 處理節氣查詢時發生錯誤: {e}")
        send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，查詢節氣小知識時發生內部錯誤，請稍候再試。")])
        return True