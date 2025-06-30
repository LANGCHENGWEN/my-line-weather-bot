import logging
from linebot.v3.messaging.models import TextMessage, ReplyMessageRequest
from config import setup_logging

# 假設這些別名在您的主程式 (app.py) 中定義並傳遞進來
MAIN_MENU_ALIAS = "main_menu_alias" # 從 app.py 傳入
TYPHOON_ZONE_ALIAS = "typhoon_zone_alias" # 從 app.py 傳入

logger = setup_logging(__name__)

def handle_typhoon_zone_menu(event, line_bot_api):
    """
    處理颱風專區子選單的邏輯。
    """
    text = event.message.text
    user_id = event.source.user_id

    logger.info(f"處理颱風專區子選單訊息來自用戶 {user_id}: {text}")

    if text == "颱風現況":
        # 這裡可以呼叫實際處理颱風現況的函數
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="正在查詢颱風現況...")]
            )
        )
    elif text == "颱風路徑圖":
        # 這裡可以呼叫實際處理颱風路徑圖的函數
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="正在生成颱風路徑圖...")]
            )
        )
    elif text == "地區影響預警":
        # 這裡可以呼叫實際處理地區影響預警的函數
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="正在查詢地區影響預警...")]
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
                messages=[TextMessage(text=f"颱風專區子選單不支援此指令: {text}\n請使用選單按鈕。")]
            )
        )