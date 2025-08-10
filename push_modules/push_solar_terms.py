# push_modules/push_solar_terms.py
import logging
from datetime import datetime
from linebot.v3.messaging.models import TextMessage, FlexMessage

from utils.line_common_messaging import send_line_push_message
from utils.firestore_manager import get_users_with_push_enabled

# 導入你已經準備好的模組
from solar_terms.solar_terms_calculator import get_today_solar_term_info
# 導入 solar_terms_handler 中新定義的輔助函式
from solar_terms.solar_terms_handler import get_solar_term_flex_message

logger = logging.getLogger(__name__)

# 推播功能的 feature_id
FEATURE_ID = "solar_terms_push"

def push_solar_terms_notification(line_bot_api_instance):
    """
    在節氣當天推播節氣小知識給所有已開啟此功能的用戶。
    """
    # 呼叫你實際的函式來判斷今天是否為節氣日，並獲取完整的資訊
    today = datetime.now().date()
    # today = datetime(2025, 8, 7).date() ***在本機測試用，日期為節氣的日期
    solar_term_data = get_today_solar_term_info(check_date=today)
    if not solar_term_data:
        logger.info("今天不是節氣日，節氣小知識推播任務跳過。")
        return

    term_name = solar_term_data.get("name", "未知節氣")
    logger.info(f"今天是節氣日：{term_name}，開始執行推播...")

    # 從資料庫獲取所有已開啟節氣推播的用戶
    enabled_users = get_users_with_push_enabled(FEATURE_ID)
    if not enabled_users:
        logger.warning("沒有用戶開啟節氣推播，任務結束。")
        return
    
    try:
        # --- 關鍵修改：呼叫輔助函式來創建 Flex Message ---
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

    except Exception as e:
        logger.error(f"處理節氣小知識推播給用戶 {user_id} 時發生錯誤: {e}", exc_info=True)
        # 如果 Flex Message 推播失敗，fallback 到一個簡單的文字訊息
        for user_id in enabled_users:
            text_message = TextMessage(text=f"【節氣小知識】\n\n今天是「{term_name}」！\n\n{solar_term_data.get('description', '無相關描述。')}\n\n希望這份小知識能為您帶來生活中的一點樂趣！")
            send_line_push_message(
                line_bot_api_instance=line_bot_api_instance,
                user_id=user_id,
                messages=[text_message]
            )