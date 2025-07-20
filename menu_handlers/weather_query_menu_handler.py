# weather_query_menu_handler.py
import logging
from linebot.v3.messaging.models import TextMessage, ReplyMessageRequest
from weather_current import current_handler
from weather_forecast import forecast_handler

# 假設這些別名在您的主程式 (app.py) 中定義並傳遞進來，或者您可以再次定義
# 為了避免循環引用，建議在 app.py 中定義並作為參數傳遞
# 或者在一個獨立的 config.py 中定義
MAIN_MENU_ALIAS = "main_menu_alias" # 從 app.py 傳入
WEATHER_QUERY_ALIAS = "weather_query_alias" # 從 app.py 傳入

logger = logging.getLogger(__name__)

def handle_weather_query_menu(event, line_bot_api):
    """
    處理天氣查詢子選單的邏輯。
    根據用戶發送的文字訊息，執行相應的動作或切換選單。
    """
    text = event.message.text
    user_id = event.source.user_id

    logger.info(f"處理天氣查詢子選單訊息來自用戶 {user_id}: {text}")

    if text == "即時天氣":
        current_handler.handle_current_message(line_bot_api, event)
    elif text == "未來預報":
        forecast_handler.handle_forecast_request(event, line_bot_api)
    elif text == "回上一頁":
        line_bot_api.link_rich_menu_alias_to_user(user_id, MAIN_MENU_ALIAS)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="已回主選單。")]
            )
        )
    else:
        # 如果收到不在子選單定義內的訊息，可以選擇回覆提示或忽略
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=f"天氣查詢子選單不支援此指令: {text}\n請使用選單按鈕。")]
            )
        )