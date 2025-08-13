# push_modules/push_solar_terms.py
"""
執行節氣小知識的推播任務。
排程系統（如 Cloud Scheduler）會定時觸發。
首先判斷今天是否為二十四節氣的其中一天；如果確定是節氣日，會從資料庫中找出所有已開啟此推播功能的使用者。
為該節氣日動態生成一個內容豐富的 Flex Message 訊息卡片，最後將這個訊息推播給所有符合條件的使用者。
包含錯誤處理機制，如果 Flex Message 生成或推播失敗，會降級（fallback）發送一個簡單的文字訊息，確保使用者至少能收到基本資訊。
"""
import logging
from datetime import datetime
from linebot.v3.messaging.models import TextMessage

from utils.line_common_messaging import send_line_push_message
from utils.firestore_manager import get_users_with_push_enabled

# 導入判斷今天是否為節氣日的函式
from solar_terms.solar_terms_calculator import get_today_solar_term_info

# 導入公共函式：獲取今天的節氣資訊並建構 Flex Message
from solar_terms.solar_terms_handler import get_solar_term_flex_message

logger = logging.getLogger(__name__)

# 推播功能的 feature_id
FEATURE_ID = "solar_terms_push"

# --- 在節氣當天推播節氣小知識給所有已開啟此功能的使用者 ---
def push_solar_terms_notification(line_bot_api_instance):
    """
    執行流程：
    1. 判斷今天是否為節氣日；如果不是，則直接結束任務，避免不必要的資源消耗。
    2. 如果是節氣日，則從資料庫中獲取所有開啟了節氣推播功能的使用者 ID 列表。
    3. 呼叫專門的函式，將節氣資訊轉換為一個美觀的 Flex Message 物件，然後遍歷使用者列表，將 Flex Message 推播給每個使用者。
    4. 包含一個 try-except 區塊，如果 Flex Message 推播失敗，會自動切換為發送一個簡單的文字訊息，以確保訊息傳達的可靠性。
    """
    # 1. 檢查當前日期是否為二十四節氣中的某一天
    """
    這是整個推播任務的第一步，也是效能優化的關鍵。
    節氣日每年只有二十四天，所以絕大多數時候這個判斷都會是 `False`。
    通過在最開始就進行這項檢查，可以讓程式在非節氣日快速結束，避免後續查詢資料庫、生成訊息、發送推播等所有耗時的操作。
    這種「預先篩選」的設計可以顯著減少系統資源的佔用，讓排程任務的執行更有效率。
    """
    today = datetime.now().date()
    # today = datetime(2025, 8, 7).date() ***在本機測試用，日期為節氣當天的日期

    solar_term_data = get_today_solar_term_info(check_date=today)
    if not solar_term_data:
        logger.info("今天不是節氣日，節氣小知識推播任務跳過。")
        return

    term_name = solar_term_data.get("name", "未知節氣")
    logger.info(f"今天是節氣日：{term_name}，開始執行推播...")

    # 2. 從 Firestore 資料庫獲取所有已開啟節氣推播的使用者
    """
    從資料庫中批量獲取所有已開啟特定推播功能的使用者 ID。
    與 `push_daily_weather.py` 中按城市分組不同，節氣推播是針對所有使用者的，不受地理位置限制。
    所以直接使用 `get_users_with_push_enabled(FEATURE_ID)` 函式來查詢所有開啟 `solar_terms_push` 這個功能的使用者。
    一次性獲取使用者的 ID 列表，這樣可以簡化後續的迴圈邏輯，直接將訊息發送給所有相關使用者。
    """
    enabled_users = get_users_with_push_enabled(FEATURE_ID)
    if not enabled_users:
        logger.warning("沒有用戶開啟節氣推播，任務結束。")
        return
    
    # 3. 呼叫公共函式 (get_solar_term_flex_message) 來創建 Flex Message，並將 Flex Message 推播給每個使用者
    # `try...except` 區塊包裹了整個消息創建和發送流程
    # 如果在創建 Flex Message 時或推播時發生任何錯誤，程式會立即捕獲這個異常，記錄詳細錯誤日誌
    try:
        """
        首先在 `for` 迴圈外部呼叫 `get_solar_term_flex_message` 一次，生成一個完整的 Flex Message 物件。
        在迴圈內，將這個相同的物件發送給每個使用者。
        這種設計避免在每個使用者迴圈中重複生成 Flex Message，顯著提高效率，特別是使用者較多時。
        """
        flex_message_to_send = get_solar_term_flex_message(solar_term_data)
        if not flex_message_to_send:
            raise ValueError("無法成功建構節氣 Flex Message。")

        messages_to_send = [flex_message_to_send]
        for user_id in enabled_users:
            send_line_push_message(
                line_bot_api_instance=line_bot_api_instance,
                user_id=user_id,
                messages=messages_to_send
            )
        logger.info("節氣小知識推播任務執行完畢。")

    # 4. 錯誤處理與降級 (Fallback)
    except Exception as e:
        """
        `except` 區塊中的邏輯是一個「降級」機制：為每個使用者生成一個簡單的 `TextMessage`。
        這種設計確保即使複雜的 Flex Message 渲染或推播失敗，使用者也不會收不到任何通知，仍然能以文字形式收到節氣資訊，提升系統的可靠性和使用者體驗。
        """
        logger.error(f"處理節氣小知識推播給用戶 {user_id} 時發生錯誤: {e}", exc_info=True)

        for user_id in enabled_users:
            text_message = TextMessage(text=f"【節氣小知識】\n\n今天是「{term_name}」！\n\n{solar_term_data.get('description', '無相關描述。')}\n\n希望這份小知識能為您帶來生活中的一點樂趣！")
            send_line_push_message(
                line_bot_api_instance=line_bot_api_instance,
                user_id=user_id,
                messages=[text_message]
            )