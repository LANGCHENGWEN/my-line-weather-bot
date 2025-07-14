import logging
from linebot.v3.messaging.models import TextMessage, ReplyMessageRequest

# 假設這些別名在您的主程式 (app.py) 中定義並傳遞進來
MAIN_MENU_ALIAS = "main_menu_alias" # 從 app.py 傳入
SETTINGS_ALIAS = "settings_alias" # 從 app.py 傳入

logger = logging.getLogger(__name__)

def handle_settings_menu_postback(event, line_bot_api):
    """
    處理設定子選單的 Postback 邏輯。
    """
    data = event.postback.data
    user_id = event.source.user_id

    logger.info(f"處理設定子選單 Postback 事件來自用戶 {user_id}，數據: {data}")

    if data == "action=toggle_daily_reminder":
        # 實現每日提醒推播的開關邏輯
        logger.info(f"用戶 {user_id} 請求切換每日提醒推播。")
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="每日提醒推播設定已更新。")]
            )
        )
    elif data == "action=toggle_typhoon_notification":
        # 實現颱風通知推播的開關邏輯
        logger.info(f"用戶 {user_id} 請求切換颱風通知推播。")
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="颱風通知推播設定已更新。")]
            )
        )
    elif data == "action=toggle_weekend_weather":
        # 實現週末天氣推播的開關邏輯
        logger.info(f"用戶 {user_id} 請求切換週末天氣推播。")
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="週末天氣推播設定已更新。")]
            )
        )
    elif data == "action=toggle_solar_terms":
        # 實現節氣小知識推播的開關邏輯
        logger.info(f"用戶 {user_id} 請求切換節氣小知識推播。")
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="節氣小知識推播設定已更新。")]
            )
        )
    # START: 新增 '切換預設城市' 的處理邏輯
    elif data == "action=change_default_city":
        # 實現切換預設城市的邏輯
        logger.info(f"用戶 {user_id} 請求切換預設城市。")
        # 這裡你可以：
        # 1. 直接回復一個文本訊息，引導用戶輸入城市
        # 2. 發送一個包含城市列表的模板訊息 (如按鈕模板、圖片地圖模板) 供用戶選擇
        # 3. 標記用戶狀態，進入「選擇城市」對話模式 (這需要更複雜的狀態管理)

        # 這裡以回復一個引導文本訊息為例
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TextMessage(text="請輸入您想設定的預設城市名稱，例如：台北市、台中市、高雄市。"),
                    # 如果有設定好的「選擇城市」富媒體菜單別名，可以一併提示
                    # TextMessage(text="您也可以點擊下方「選擇城市」按鈕。")
                ]
            )
        )

    # Note: "回上一頁"按鈕在 settings_menu.json 中仍然是 type="message"，
    # 所以它會在 handle_message 中被處理，而不是這裡。
    else:
        logger.warning(f"收到未知的設定子選單 Postback 數據: {data}")