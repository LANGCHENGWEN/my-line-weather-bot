# settings/settings_handler.py
import logging
from linebot.v3.messaging.models import TextMessage, FlexMessage, FlexBubble
from linebot.v3.webhooks.models import PostbackEvent
from .create_push_setting_flex_message import create_push_setting_flex_message
from utils.line_common_messaging import send_line_reply_message

logger = logging.getLogger(__name__)

# 模擬資料庫，請替換成你的實際資料庫操作
user_settings_db = {}

# 1. 根據 feature_id 獲取功能的名稱
# 將 feature_map 定義在模組層級，讓所有函式都可以使用
feature_map = {
    "daily_reminder_push"       : "每日天氣",
    "typhoon_notification_push" : "颱風通知",
    "weekend_weather_push"      : "週末天氣",
    "solar_terms_push"          : "節氣小知識"
}

def handle_settings_postback(api, event):
    """
    處理推播設定的 Postback 事件。
    
    Args:
        api: LineBotApi 實例。
        event: PostbackEvent 物件。
    """
    user_id = event.source.user_id
    reply_token = event.reply_token

    # 在這裡加入日誌
    logger.debug(f"收到的 Postback data: {event.postback.data}")

    logger.info(f"[SolarTermsHandler] 收到推播設定請求。用戶: {user_id}")

    # 1. 解析 postback.data
    data = event.postback.data
    query_params = dict(param.split('=') for param in data.split('&'))
    action_type = query_params.get('action')

    # 直接使用 action 作為 feature_id
    # 處理來自選單按鈕的 Postback
    if action_type in feature_map:
        feature_id = action_type
        logger.debug(f"解析出的 feature_id: {feature_id}")

        # 獲取使用者目前的設定狀態
        is_enabled = user_settings_db.get(user_id, {}).get(feature_id, False)

        # 取得功能名稱，如果找不到則返回空字串
        feature_name = feature_map.get(feature_id, "")
        logger.debug(f"找到的 feature_name: {feature_name}")

        flex_message_to_send = create_push_setting_flex_message(feature_id, is_enabled, feature_name)
        send_line_reply_message(api, reply_token, [flex_message_to_send])

    # 處理來自 Flex Message 內「開啟/關閉」按鈕的 Postback
    elif action_type == 'set_status':
        feature_id = query_params.get('feature')
        status_str = query_params.get('status')
        
        if feature_id and status_str:
            is_enabled = status_str == 'on'
            feature_name = feature_map.get(feature_id, "")

            # 模擬更新資料庫
            if user_id not in user_settings_db:
                user_settings_db[user_id] = {}
            user_settings_db[user_id][feature_id] = is_enabled

            status_text = "開啟" if is_enabled else "關閉"
            message_text = f"「{feature_name}」推播已成功設定為：{status_text}。"
            send_line_reply_message(api, reply_token, [TextMessage(text=message_text)])

    else:
        # 如果 feature_id 無效，可以發送一個錯誤訊息
        logger.error(f"收到帶有無效 action 的 Postback: {action_type}")
        send_line_reply_message(api, reply_token, [TextMessage(text="無效的推播設定指令。")])

    """
    # 2. 更新資料庫設定
    if user_id not in user_settings_db:
        user_settings_db[user_id] = {}
    user_settings_db[user_id][feature_id] = is_enabled
    """

    """
    # 3. 回覆使用者設定成功的訊息
    feature_name = {
        "daily_reminder": "每日提醒",
        "typhoon_alert": "颱風通知",
        "weekend_weather": "週末天氣",
        "solar_terms": "節氣小知識"
    }.get(feature_id, "該推播")
    status_text = "開啟" if is_enabled else "關閉"
    """