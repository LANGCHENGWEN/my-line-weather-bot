# push_modules/push_typhoon_notification.py
"""
執行颱風警報的推播任務。
排程系統（如 Cloud Scheduler）會定時觸發，每隔一段時間檢查是否有新的颱風警報發布。
核心邏輯：
1. 從中央氣象署獲取最新的颱風警報數據。
2. 將當前的警報編號與資料庫中上次推播的記錄進行比對；如果是新的警報，則動態生成一個內容豐富的 Flex Message 訊息。
4. 從資料庫中找出所有開啟了颱風推播功能的使用者，將生成的 Flex Message 推播給這些使用者。
6. 最後，將這次的警報編號寫入資料庫，以避免下次重複推播。
7. 包含完善的錯誤處理和降級機制，確保在推播失敗時仍能發送文字訊息。
"""
import logging
from linebot.v3.messaging.models import TextMessage

from utils.line_common_messaging import send_line_push_message
from utils.firestore_manager import get_system_metadata, set_system_metadata, get_users_with_push_enabled

# 這裡只導入 TyphoonLogic，因為它封裝了所有後續步驟
from typhoon.typhoon_handler import TyphoonLogic

logger = logging.getLogger(__name__)

# 推播功能的 feature_id
FEATURE_ID = "typhoon_notification_push"
# 儲存上一次推播的颱風警報編號，避免重複推播
LAST_TYPHOON_ID_KEY = "last_typhoon_id"

# --- 檢查是否有新的颱風警報，並推播給所有已開啟此功能的使用者 ---
def check_and_push_typhoon_notification(line_bot_api_instance):
    """
    執行流程：
    1. 初始化 TyphoonLogic 類別，該類別負責所有數據獲取和處理的細節。
    2. 呼叫 TyphoonLogic 的方法，一次性獲取最新的颱風數據和預先建立好的 Flex Message。
    3. 提取當前警報的唯一 ID，並與資料庫中上次推播的 ID 進行比對，以實現防重複推播機制。
    4. 如果是新的警報，則從資料庫中獲取所有已開啟推播的使用者，將訊息發送給這些使用者，並在發送成功後，更新資料庫中的上次推播 ID。
    5. 如果在任何環節發生錯誤，捕獲異常並發送一個簡短的文字訊息作為備用，確保使用者不會錯過重要通知。
    """
    logger.info("開始檢查颱風警報...")

    # 1. 初始化 TyphoonLogic
    try:
        typhoon_logic = TyphoonLogic()
    except ValueError as e:
        logger.critical(f"初始化 TyphoonLogic 失敗: {e}")
        return
    
    # 2. 呼叫 `TyphoonLogic` 的核心方法來獲取所有颱風相關的數據和訊息
    """
    將複雜的數據獲取（CWA API 呼叫）、解析和 Flex Message 建立過程都封裝在 `TyphoonLogic` 內部。
    這樣設計的好處是 `check_and_push_typhoon_notification` 這個函式本身不需要知道處理的細節，只需專注於「推播」這個核心任務。
    如果 `typhoon_logic.get_typhoon_info_and_message()` 返回 `None`，表示目前沒有有效的颱風警報，程式就可以提前結束，節省後續不必要的運算和資料庫操作，提升程式碼的清晰度和執行效率。
    """
    typhoon_info_and_message = typhoon_logic.get_typhoon_info_and_message()
    if not typhoon_info_and_message:
        logger.info("目前沒有颱風警報資訊或數據處理失敗。")
        return
    
    # 執行 typhoon_info_and_message，然後回傳多個值，分別賦予給 parsed_typhoon_data 和 typhoon_flex_message 這兩個變數
    parsed_typhoon_data, typhoon_flex_message = typhoon_info_and_message

    # 3. 從解析後的數據中提取 typhoon_id 和 typhoon_name
    typhoon_id = parsed_typhoon_data["currentStatus"].get("typhoon_id")
    typhoon_name = parsed_typhoon_data["currentStatus"].get("typhoonName")
    if not typhoon_id:
        logger.warning("無法從解析後的數據中取得颱風 ID，無法進行重複性檢查。")
        return

    """
    實現「防重複推播」的關鍵邏輯。
    颱風警報的資料會持續更新，但警報的「編號」在警報期間通常是固定的。
    為了避免在每次定時檢查時都重複發送同一份警報，將上次成功推播的警報 ID 儲存在一個全域性的資料庫位置（`get_system_metadata`）。
    在每次執行推播任務時，將當前獲取的颱風 ID 與儲存的 ID 進行比對。
    如果兩者相同，表示這份警報已經推播過，程式會直接結束，這樣可以有效避免向使用者發送重複訊息，同時減少不必要的 API 呼叫和運算，提高使用者體驗和系統效率。
    """
    last_pushed_typhoon_id = get_system_metadata(LAST_TYPHOON_ID_KEY, None) # 從資料庫獲取上一次推播的颱風警報 ID
    if typhoon_id == last_pushed_typhoon_id: # 將 typhoon_id 與資料庫中的記錄比對，以判斷是否需要推播
        logger.info(f"颱風警報 ID {typhoon_id} 已推播過，不重複發送。")
        return

    logger.info(f"發現新的颱風警報：{typhoon_name} (ID: {typhoon_id})，開始推播。")
    
    # 4. 從資料庫獲取所有已開啟颱風通知的使用者
    """
    用一個單一的資料庫查詢來獲取所有符合條件的使用者 ID 列表，避免對每個使用者進行單獨查詢的低效操作。
    如果沒有使用者啟用此功能，程式會記錄日誌並結束，但仍會更新 `last_typhoon_id`，為了確保即使沒有使用者收到通知，下次檢查時也不會將這個舊的警報視為「新」的而再次嘗試推播，這是一個重要的防護措施。
    """
    enabled_users = get_users_with_push_enabled(FEATURE_ID)
    if not enabled_users:
        logger.warning("沒有用戶開啟颱風通知，任務結束。")
        # 即使沒有使用者，我們也應該記錄這次警報，以防下次推播
        set_system_metadata(**{LAST_TYPHOON_ID_KEY: typhoon_id}) # 寫入這次推播的颱風 ID
        return
        
    # 將 Flex Message 推播給每個使用者
    # `try...except` 區塊包裹了整個推播過程
    try:
        """
        將預先創建好的 `typhoon_flex_message` 儲存為一個列表，然後在迴圈中將這個訊息推播給每個使用者。
        整個推播迴圈成功完成後，程式會呼叫 `set_system_metadata` 將當前的 `typhoon_id` 寫入資料庫。
        這種設計確保只有在確認所有推播都已發送後，才會更新狀態，這是一個標準的「提交」模式，避免在推播過程中途失敗，但狀態卻被錯誤更新的情況。
        """
        messages_to_send = [typhoon_flex_message]
        for user_id in enabled_users:
            send_line_push_message(
                line_bot_api_instance=line_bot_api_instance,
                user_id=user_id,
                messages=messages_to_send
            )

        # 推播完成後，更新資料庫中的上次推播 ID
        set_system_metadata(**{LAST_TYPHOON_ID_KEY: typhoon_id})
        logger.info("颱風通知推播任務執行完畢。")

    # 5. 錯誤處理與降級 (Fallback)
    except Exception as e:
        """
        如果在推播過程中發生任何異常（例如 LINE API 的連線問題），程式會捕獲這個錯誤，記錄詳細日誌，然後執行 `except` 區塊中的「降級」邏輯。
        降級邏輯會為所有使用者發送一個包含基本資訊的 `TextMessage`，這樣即使複雜的 Flex Message 無法發送，使用者仍然能收到重要的颱風通知。
        確保在緊急情況下的訊息傳達可靠性，這是這類警報系統的關鍵特性。
        """
        logger.error(f"推播颱風警報時發生錯誤: {e}", exc_info=True)
        
        fallback_message = TextMessage(
            text=f"【颱風警報】\n\n颱風名稱：{typhoon_name}\n\n目前無法顯示詳細資訊，請前往中央氣象署官網查看最新動態。\n\nhttps://www.cwa.gov.tw"
        )

        for user_id in enabled_users:
            send_line_push_message(
                line_bot_api_instance=line_bot_api_instance,
                user_id=user_id,
                messages=[fallback_message]
            )