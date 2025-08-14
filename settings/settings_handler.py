# settings/settings_handler.py
"""
LINE Bot 用於處理與「推播設定」相關的 Postback 事件的核心模組。
主要職責：
1. 解析 Postback 事件：從用戶點擊按鈕後發送的 Postback 數據中，解析出動作類型（`action`）和功能 ID（`feature`）等參數。
2. 生成互動介面：當用戶從 Rich Menu 點擊某個推播功能（例如「每日天氣推播」）時，會查詢資料庫獲取用戶當前的設定狀態，然後動態生成一個包含「開啟/關閉」按鈕的 Flex Message，並回覆給用戶。
3. 更新數據庫：當用戶在 Flex Message 介面中點擊「開啟」或「關閉」按鈕時，會更新資料庫中該用戶對應功能的設定狀態。
4. 提供回饋：在完成設定更新後，向用戶發送一個確認訊息，讓用戶知道操作已成功。
"""
import logging
from linebot.v3.messaging.models import TextMessage
from utils.line_common_messaging import send_line_reply_message
from utils.firestore_manager import get_user_push_settings, update_user_push_setting
from .create_push_setting_flex_message import create_push_setting_flex_message

logger = logging.getLogger(__name__)

# --- 根據 feature_id 獲取功能的名稱 ---
"""
這個字典 `feature_map` 是一個常數，用於將後端使用的功能 ID（例如 `daily_reminder_push`）映射到對應用戶介面顯示的名稱（例如「每日天氣」）。
1. 集中管理：將 ID 到名稱的對應關係集中在一個地方，方便未來的修改和擴展。
2. 提高可讀性：在程式碼中使用 `feature_map.get(feature_id)` 比硬編碼字串更清晰，也避免在多處重複定義相同的名稱。
3. 國際化/在地化：如果未來需要支援多國語言，只需修改這個字典的值，而不需要修改處理邏輯中的程式碼。
"""
feature_map = {
    "daily_reminder_push"       : "每日天氣",
    "typhoon_notification_push" : "颱風通知",
    "weekend_weather_push"      : "週末天氣",
    "solar_terms_push"          : "節氣小知識"
}

def handle_settings_postback(api, event):
    """
    根據 Postback 事件的 `data` 內容，執行不同的設定操作。
    首先解析 Postback 數據，然後根據 `action` 類型進行分流處理：
    1. 如果 `action_type` 是某個推播功能的 ID，會生成並回覆一個 Flex Message 介面。
    2. 如果 `action_type` 是 `set_status`，會更新資料庫中的用戶設定，並回覆文字確認。
    """
    user_id = event.source.user_id
    reply_token = event.reply_token

    logger.debug(f"收到的 Postback data: {event.postback.data}")
    logger.info(f"[SolarTermsHandler] 收到推播設定請求。用戶: {user_id}")

    # --- 解析從 Postback 事件中接收到的 `data` 字串 ---
    # `try-except` 錯誤處理，應對格式不正確的 `data` 字串，確保程式在收到無效輸入時不會崩潰
    data = event.postback.data
    try:
        query_params = dict(param.split('=') for param in data.split('&')) # 將字串轉換為一個方便存取的字典
    except ValueError:
        logger.error(f"Postback data 格式錯誤: {data}")
        send_line_reply_message(api, reply_token, [TextMessage(text="無效的設定指令。")])
        return
    
    # 從字典中，取出鍵（key）為 'action' 的值（value）
    action_type = query_params.get('action')

    # --- 處理來自 Rich Menu 設定子選單中推播按鈕的點擊事件 ---
    if action_type in feature_map: # 判斷 action_type 是否為已定義的推播功能 ID
        """
        當用戶從 Rich Menu 點擊「每日天氣推播」時，Postback `data` 會是 `action=daily_reminder_push`。
        這段邏輯偵測到這個 `action`，然後從資料庫讀取用戶當前的推播設定狀態。
        接著呼叫 `create_push_setting_flex_message` 函式，並將狀態傳入，動態生成一個帶有「已開啟」或「已關閉」字樣的 Flex Message。
        最後將這個 Flex Message 作為回覆發送給用戶。
        """
        feature_id = action_type
        logger.debug(f"解析出的 feature_id: {feature_id}")

        # 從資料庫獲取用戶目前的設定狀態
        user_push_settings = get_user_push_settings(user_id)
        is_enabled = user_push_settings.get(feature_id, False)

        # 取得功能名稱，如果找不到則返回空字串
        feature_name = feature_map.get(feature_id, "")
        logger.debug(f"找到的 feature_name: {feature_name}")

        # 動態生成 Flex Message，並發送
        flex_message_to_send = create_push_setting_flex_message(feature_id, is_enabled, feature_name)
        send_line_reply_message(api, reply_token, [flex_message_to_send])

    # --- 處理用戶在 Flex Message 介面中點擊「開啟」或「關閉」按鈕的 Postback ---
    elif action_type == 'set_status': # 判斷 action_type 是否為 'set_status'
        """
        - 統一處理邏輯：Flex Message 中的按鈕 `data` 格式為 `action=set_status&feature=...&status=...`。
          這個邏輯會偵測到 `action=set_status`，然後從 `data` 中解析出具體的 `feature_id` 和 `status`。
          這種統一的格式可以使用一套通用的邏輯來處理所有推播功能的狀態切換。
        - 更新數據庫：呼叫 `update_user_push_setting` 函式，將用戶的推播設定狀態持久化到資料庫中，確保設定被正確保存。
        - 提供回饋：在數據庫更新成功後，程式會向用戶發送一個簡短的 `TextMessage`，確認操作已經完成。
        """
        feature_id = query_params.get('feature')
        status_str = query_params.get('status')
        
        if feature_id and status_str:
            is_enabled = status_str == 'on'
            feature_name = feature_map.get(feature_id, "")

            # 呼叫資料庫管理模組函式來更新設定
            update_user_push_setting(user_id, feature_id, is_enabled)
            
            # 發送訊息，確認操作已經完成
            status_text = "開啟" if is_enabled else "關閉"
            message_text = f"「{feature_name}」推播已成功設定為：{status_text}。"
            send_line_reply_message(api, reply_token, [TextMessage(text=message_text)])

    else:
        # 如果 feature_id 無效，發送一個錯誤訊息
        logger.error(f"收到帶有無效 action 的 Postback: {action_type}")
        send_line_reply_message(api, reply_token, [TextMessage(text="無效的推播設定指令。")])