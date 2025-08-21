# utils/line_common_messaging.py
"""
LINE 訊息傳送的通用工具庫，封裝所有與 LINE Messaging API 傳送訊息相關的邏輯。
將發送訊息的邏輯集中管理，避免在其他模組中重複編寫相同的程式碼。
明確區分「回覆（Reply）」和「推播（Push）」兩種不同的訊息發送情境，並提供專門的函式。
"""
import json
import logging
from typing import List, Union
from linebot.v3.messaging import MessagingApi
from linebot.v3.messaging.models import Message, ReplyMessageRequest, PushMessageRequest
from linebot.v3.exceptions import InvalidSignatureError

from utils.flex_templates import build_hello_flex
from utils.message_builder import format_text_message

logger = logging.getLogger(__name__)

# --- 向指定用戶發送 LINE 推播訊息（主動發送）---
def send_line_push_message(line_bot_api_instance, user_id: str, messages: List[Message]):
    """
    接收一個用戶 ID 和一個或多個 LINE Message 物件，並構建一個推播請求。
    此函式不需要 reply_token，因為它是機器人主動觸發的，例如定時推播。
    """
    try:
        # 1. 前置檢查
        # 如果傳入的訊息列表是空的，直接記錄警告並返回，避免不必要的 API 呼叫，提高效率並防止潛在的錯誤
        if not messages:
            logger.warning("沒有訊息可推播。")
            return

        # 2. 構建並發送推播請求
        # 構建 PushMessageRequest 物件，這是 LINE SDK V3 所要求的格式
        push_message_request = PushMessageRequest(
            to=user_id,
            messages=messages
        )

        # 使用 Line API 實例發送訊息
        line_bot_api_instance.push_message(push_message_request)

        logger.info(f"訊息已成功推播給用戶 ID: {user_id}")
    except Exception as e:
        # 捕捉發送過程中的任何錯誤，並詳細記錄，包括堆疊追蹤資訊，以便除錯
        logger.error(f"推播訊息給 {user_id} 時發生錯誤: {e}", exc_info=True)

# --- 對用戶的訊息進行回覆 ---
def send_line_reply_message(line_bot_api_instance: MessagingApi, reply_token: str, messages: Union[Message, List[Message]], user_id: str = None):
    """
    用 LINE 提供的 `reply_token` 在用戶發送訊息後進行回覆。
    處理單個或多個訊息物件，並包含一個重要的容錯機制：如果回覆失敗（通常是因為 `reply_token` 過期），會嘗試將訊息作為推播（Push）訊息重新發送。
    """
    # 1. 處理訊息格式
    # 確保無論傳入的是單個 `Message` 物件還是 `List[Message]`，`messages` 變數都會是一個列表，簡化後續的程式碼邏輯
    if not isinstance(messages, list):
        messages = [messages]

    # 2. 構建回覆請求物件
    reply_message_request = ReplyMessageRequest(
        reply_token=reply_token,
        messages=messages
    )
    
    logger.debug(f"準備發送回覆。Reply Token: {reply_token}")
    try:
        # 在開發和測試階段輸出詳細的日誌，將訊息物件轉換為字典列表以便輸出，方便檢查即將發送的訊息內容是否正確
        messages_as_dict = [m.to_dict() for m in messages]
        # 將複雜的訊息物件轉換為可讀的 JSON 字串，並在發送前印出來，幫助開發者在不依賴 LINE Webhook 頁面就能確認訊息結構
        logger.debug(f"準備發送的訊息內容: {json.dumps(messages_as_dict, indent=2, ensure_ascii=False)}")
    except Exception as e:
        # 如果訊息物件無法被序列化，會捕獲異常並記錄，確保日誌功能本身不會導致程式崩潰
        logger.error(f"無法序列化訊息物件用於日誌: {e}")

    # 3. 發送訊息與錯誤處理
    try:
        line_bot_api_instance.reply_message(reply_message_request)
        logger.info(f"成功回覆訊息 (reply_token: {reply_token})")
    except InvalidSignatureError as e:
        """
        `InvalidSignatureError` 通常是由於 `reply_token` 過期或無效導致的。
        如果發生這種情況，標準的 `reply_message` 呼叫會失敗。
        這段程式碼提供一個重要的備用方案：如果錯誤訊息中包含「Invalid reply token」，並且有用戶 ID，就嘗試將訊息作為推播訊息重新發送。
        這大大提高了訊息傳送的成功率，尤其是在處理延遲的 Webhook 請求時。
        """
        logger.error(f"回覆訊息失敗 (API 錯誤 - reply_token: {reply_token}): ({e.status})\nReason: {e.reason}\nHTTP response body: {e.body}", exc_info=True)
        if "Invalid reply token" in e.body and user_id:
            logger.warning(f"Reply token 無效，嘗試將訊息作為 Push 訊息發送給用戶 {user_id}。")
            try:
                push_request = PushMessageRequest(
                    to=user_id,
                    messages=messages
                )
                line_bot_api_instance.push_message(push_request)
                logger.info(f"成功將訊息作為 Push 訊息發送給用戶 {user_id} (原 reply_token: {reply_token})。")
            except InvalidSignatureError as push_e:
                logger.error(f"Push 訊息發送失敗 (API 錯誤 - 用戶 {user_id}): ({push_e.status})\nReason: {push_e.reason}\nHTTP response body: {push_e.body}", exc_info=True)
            except Exception as push_e:
                logger.error(f"Push 訊息發送時發生未知錯誤 (用戶 {user_id}): {push_e}", exc_info=True)
        else:
            logger.error(f"回覆訊息失敗 (非 reply token 錯誤 或 無法推播) - reply_token: {reply_token}", exc_info=True)
    except Exception as e:
        logger.error(f"回覆訊息失敗 (未知錯誤 - reply_token: {reply_token}): {e}", exc_info=True)

# --- 發送歡迎 Flex 訊息卡片 ---
def send_hello_message(line_bot_api_instance, user_id: str, reply_token: str):
    """
    使用 `build_hello_flex` 函式建立一個 Flex Message，並透過 `send_line_reply_message` 發送。
    如果 Flex Message 建立或發送失敗，會回退（fallback）到發送一個純文字訊息，確保用戶總能收到回覆。
    """
    try:
        flex_msg = build_hello_flex()
        send_line_reply_message(line_bot_api_instance, reply_token, flex_msg)
        logger.info(f"已發送 Flex 歡迎語給用戶 ID: {user_id}")
    except Exception as e:
        logger.error(f"發送 Flex 歡迎訊息失敗，改用純文字：{e}", exc_info=True)
        fallback_text = (
            "哈囉！您好～我是暖心天氣語。\n"
            "請先輸入您想預設的城市名稱，例如「台中市」或「台北市」，讓我幫您設定預設城市！"
        )
        send_line_reply_message(
            line_bot_api_instance,
            reply_token,
            format_text_message(fallback_text)
        )

# --- 在 API 請求失敗時，向用戶發送一個友善的錯誤回覆 ---
def send_api_error_message(line_bot_api_instance, user_id: str, reply_token: str, location_name: str = ""):
    """
    根據是否有地點名稱來動態生成錯誤訊息，並透過 `send_line_reply_message` 傳送。
    """
    text = f"抱歉，目前無法取得{' ' + location_name if location_name else ''}的天氣資訊，請稍候再試。"
    message_to_send = format_text_message(text)
    send_line_reply_message(line_bot_api_instance, reply_token, [message_to_send])
    logger.warning(f"已發送 API 錯誤訊息給用戶 ID: {user_id}")