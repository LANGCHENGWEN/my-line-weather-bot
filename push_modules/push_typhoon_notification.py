# push_modules/push_typhoon_notification.py
import logging
from linebot.v3.messaging.models import TextMessage, FlexMessage

from config import CWA_API_KEY

from utils.line_common_messaging import send_line_push_message
from utils.user_data_manager import get_users_with_push_enabled, set_user_metadata, get_user_metadata

# 導入你已經準備好的模組
# 這裡我們只導入 TyphoonLogic，因為它封裝了所有後續步驟
from typhoon.typhoon_handler import TyphoonLogic

logger = logging.getLogger(__name__)

# 推播功能的 feature_id
FEATURE_ID = "typhoon_notification_push"
# 用於儲存上一次推播的颱風警報編號，避免重複推播
LAST_TYPHOON_ID_KEY = "last_typhoon_id"
# 定義一個特殊的 user_id 來儲存系統級的元數據
SYSTEM_USER_ID = "system"

def check_and_push_typhoon_notification(line_bot_api_instance):
    """
    檢查是否有新的颱風警報，並推播給所有已開啟此功能的用戶。
    """
    logger.info("開始檢查颱風警報...")

    # 初始化 TyphoonLogic
    try:
        typhoon_logic = TyphoonLogic()
    except ValueError as e:
        logger.critical(f"初始化 TyphoonLogic 失敗: {e}")
        return
    
    # --- 關鍵修改點：呼叫新的方法一次性獲取所有需要的資訊 ---
    typhoon_info_and_message = typhoon_logic.get_typhoon_info_and_message()
    if not typhoon_info_and_message:
        logger.info("目前沒有颱風警報資訊或數據處理失敗。")
        return
    
    parsed_typhoon_data, typhoon_flex_message = typhoon_info_and_message

    # 從解析後的數據中提取 typhoon_id
    typhoon_id = parsed_typhoon_data["currentStatus"].get("typhoon_id")
    typhoon_name = parsed_typhoon_data["currentStatus"].get("typhoonName")
    if not typhoon_id:
        logger.warning("無法從解析後的數據中取得颱風 ID，無法進行重複性檢查。")
        return
    
    # 從資料庫獲取上一次推播的颱風警報 ID
    # 這裡我們需要一個單獨的「系統級」或「全域」元數據來儲存這個資訊
    # 為了簡化，我們直接在 user_data_manager 中新增一個專門的鍵來儲存
    # 這部分需要修改 user_data_manager，以支持全域元數據
    # 為了範例，我們假設你有一個這樣的函式

    # 將 typhoon_id 與資料庫中的記錄比對，以判斷是否需要推播
    last_pushed_typhoon_id = get_user_metadata(SYSTEM_USER_ID, LAST_TYPHOON_ID_KEY, None)
    if typhoon_id == last_pushed_typhoon_id:
        logger.info(f"颱風警報 ID {typhoon_id} 已推播過，不重複發送。")
        return

    logger.info(f"發現新的颱風警報：{typhoon_name} (ID: {typhoon_id})，開始推播。")
    
    # 從資料庫獲取所有已開啟颱風通知的用戶
    enabled_users = get_users_with_push_enabled(FEATURE_ID)
    if not enabled_users:
        logger.warning("沒有用戶開啟颱風通知，任務結束。")
        # 即使沒有用戶，我們也應該記錄這次警報，以防下次推播
        set_user_metadata(SYSTEM_USER_ID, **{LAST_TYPHOON_ID_KEY: typhoon_id})
        return
        
    try:
        messages_to_send = [typhoon_flex_message]
        
        for user_id in enabled_users:
            send_line_push_message(
                line_bot_api_instance=line_bot_api_instance,
                user_id=user_id,
                messages=messages_to_send
            )

        # 推播完成後，更新資料庫中的紀錄
        set_user_metadata(SYSTEM_USER_ID, **{LAST_TYPHOON_ID_KEY: typhoon_id})
        logger.info("颱風通知推播任務執行完畢。")

    except Exception as e:
        logger.error(f"推播颱風警報時發生錯誤: {e}", exc_info=True)
        # 如果 Flex Message 推播失敗，fallback 到一個簡單的文字訊息
        fallback_message = TextMessage(
            text=f"【颱風警報】\n\n颱風名稱：{typhoon_name}\n\n目前無法顯示詳細資訊，請前往中央氣象署官網查看最新動態。\n\nhttps://www.cwa.gov.tw"
        )
        for user_id in enabled_users:
            send_line_push_message(
                line_bot_api_instance=line_bot_api_instance,
                user_id=user_id,
                messages=[fallback_message]
            )