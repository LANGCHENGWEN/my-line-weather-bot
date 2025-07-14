# menu_handlers/general_message_handler.py
import logging
from linebot.v3.messaging.models import TextMessage, ReplyMessageRequest

logger = logging.getLogger(__name__)

def handle_general_message(line_bot_api, event):
    """
    處理通用文字訊息，包括問候語和未識別的訊息。
    """
    text = event.message.text
    reply_token = event.reply_token  # 從事件中獲取回覆令牌
    user_id = event.source.user_id # 獲取用戶 ID 用於日誌

    logger.info(f"處理通用訊息來自用戶 {user_id}: {text}")

    if "你好" in text:
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text="哈囉！歡迎使用天氣查詢機器人！")]
            )
        )
    elif "謝謝" in text:
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text="不客氣！很高興為您服務。")]
            )
        )
    else:
        # 如果不是以上任何指令，則可能是用戶輸入的自由文字或未處理的訊息
        logger.info(f"收到未處理的文字訊息: {text}")
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=f"您說了: {text}\n請使用選單操作功能或輸入特定關鍵字。")]
            )
        )