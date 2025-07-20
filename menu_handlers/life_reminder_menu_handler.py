# life_reminder_menu_handler.py
import logging
from linebot.v3.messaging.models import TextMessage, ReplyMessageRequest
# 假設這些別名在您的主程式 (app.py) 中定義並傳遞進來
MAIN_MENU_ALIAS = "main_menu_alias" # 從 app.py 傳入
LIFE_REMINDER_ALIAS = "life_reminder_alias" # 從 app.py 傳入

logger = logging.getLogger(__name__)

def handle_life_reminder_menu(event, line_bot_api):
    """
    處理生活提醒子選單的邏輯。
    """
    text = event.message.text
    user_id = event.source.user_id

    logger.info(f"處理生活提醒子選單訊息來自用戶 {user_id}: {text}")

    if text == "穿搭建議":
        # 這裡可以呼叫實際處理穿搭建議的函數
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="正在提供穿搭建議...")]
            )
        )
    elif text == "週末天氣":
        # 這裡可以呼叫實際處理週末天氣的函數
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="正在查詢週末天氣...")]
            )
        )
    elif text == "節氣小知識":
        # 這裡可以呼叫實際處理節氣小知識的函數
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="正在提供節氣小知識...")]
            )
        )
    elif text == "回上一頁":
        line_bot_api.link_rich_menu_alias_to_user(user_id, MAIN_MENU_ALIAS)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="已回主選單。")]
            )
        )
    else:
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=f"生活提醒子選單不支援此指令: {text}\n請使用選單按鈕。")]
            )
        )