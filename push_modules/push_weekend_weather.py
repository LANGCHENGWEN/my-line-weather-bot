# push_modules/push_weekend_weather.py
"""
執行週末天氣預報的推播任務。
排程系統（如 Cloud Scheduler）會定時觸發。
從資料庫中讀取所有已設定預設城市並開啟週末推播功能的使用者。
與每日推播不同，這裡是對於每個城市呼叫一個專門處理週末天氣的函式來獲取並生成訊息。
最後，將這個訊息推播給所有屬於該城市的使用者。
"""
import logging
from datetime import datetime

from utils.line_common_messaging import send_line_push_message
from utils.firestore_manager import get_users_by_city, get_user_push_settings

# 導入已經封裝好 Flex Message 的函式
from weekend_weather.weekend_handler import create_weekend_weather_message

logger = logging.getLogger(__name__)

# 推播功能的 feature_id
FEATURE_ID = "weekend_weather_push"

# --- 推播週末天氣預報給所有已開啟此功能的使用者 ---
def push_weekend_weather_notification(line_bot_api_instance):
    """
    執行流程：
    1. 首先檢查當前日期是否為星期五，以確保任務只在正確的時機執行。
    2. 從資料庫中獲取所有需要推播的使用者，並按城市分組。
    3. 遍歷每個城市，呼叫 `create_weekend_weather_message` 函式來獲取週末天氣的訊息。
    4. 針對該城市下的每一位使用者，再次檢查他們是否仍啟用推播功能；如果啟用，則將預先建立好的 Flex Message 推播給該使用者。
    5. 整個過程都會有詳細的日誌記錄，以追蹤任務的執行狀況和潛在錯誤。
    """
    # 1. 檢查今天是否為星期五，以確保手動觸發時邏輯正確
    """
    重要的防護措施，確保推播任務只在預定的時間執行。
    雖然這個函式會由一個排程系統設定在星期五觸發，但在開發或維護過程中，這個函式可能會被手動或錯誤的在其他日期觸發。
    透過這個檢查，可以防止程式在非預期時間執行，避免向使用者發送錯誤的訊息，也防止對外部 API 和資料庫的不必要呼叫，是提高系統健壯性的好方法。
    """
    if datetime.now().weekday() != 4: # 4 代表星期五
        logger.info("今天不是星期五，週末天氣推播任務跳過。")
        return

    logger.info("開始執行週末天氣推播任務...")
    
    # 2. 從資料庫中批量獲取所有已設定預設城市的使用者，並按城市分組
    """
    將使用者按城市分組可以極大的提高效率。
    程式只需要為每個城市呼叫一次天氣預報 API，而不是為每個使用者都呼叫一次。
    這種策略減少了對外部服務的請求次數，降低延遲，同時也優化資源使用。
    """
    all_users_by_city = get_users_by_city()
    if not all_users_by_city:
        logger.warning("沒有用戶資料，推播任務結束。")
        return

    # 3. 遍歷每個城市，呼叫 create_weekend_weather_message 函式，來取得指定城市的週末天氣訊息
    for city, user_ids in all_users_by_city.items():
        """
        將「獲取天氣數據」、「解析數據」和「創建 Flex Message」等複雜邏輯都封裝在一個函式中。
        這樣做可以使 `push_weekend_weather_notification` 這個函式保持精簡和專注，它的職責就只是「檢查是否為星期五」和「將訊息推播給使用者」，實現關注點分離，讓程式碼更易讀、易維護。
        """
        try:
            # 直接呼叫 create_weekend_weather_message 函式
            messages_to_send = create_weekend_weather_message(city)

            # 4. 為每個使用者發送推播前，再次確認他們是否仍啟用此功能
            if messages_to_send:
                """
                這與每日天氣推播的邏輯相同，是為了確保使用者收到的推播是基於他們最新的設定。
                雖然 `get_users_by_city` 提供了已設定城市的使用者列表，但使用者可能在推播任務開始後，隨時關閉這項功能。
                透過在發送前進行一次即時查詢（`get_user_push_settings`），可以確保推播的準確性，避免向已關閉推播的使用者發送訊息。
                """
                for user_id in user_ids:
                    try: # 在發送推播前，會為每個使用者單獨查詢，確認他們是否開啟了 weekend_weather_push
                        user_settings = get_user_push_settings(user_id)
                        if user_settings.get(FEATURE_ID):
                            logger.info(f"正在為用戶 {user_id[:8]}... 推播 {city} 的週末天氣。")

                            # 發送 Flex Message
                            send_line_push_message(
                                line_bot_api_instance=line_bot_api_instance,
                                user_id=user_id,
                                messages=messages_to_send
                            )

                            logger.info(f"成功為用戶 {user_id[:8]}... 推播 {city} 的週末天氣。")
                        else:
                            logger.debug(f"用戶 {user_id[:8]}... 已關閉週末天氣推播，跳過。")

                    except Exception as e:
                        logger.error(f"為用戶 {user_id[:8]}... 推播 {city} 的週末天氣時發生錯誤: {e}", exc_info=True)
            else:
                logger.warning(f"無法為城市 {city} 產生訊息，跳過推播。")

        # 5. 處理針對單一城市推播時發生的所有錯誤
        except Exception as e:
            # 確保即使某個城市在獲取天氣數據或處理時發生錯誤，整個推播任務也不會因此中斷
            # 程式會記錄錯誤，然後繼續處理下一個城市，這樣可以最大程度的確保其他城市的使用者仍然能夠收到推播訊息，提高系統的穩定性和可靠性
            logger.error(f"處理城市 {city} 的週末天氣推播時發生錯誤: {e}", exc_info=True)

    logger.info("週末天氣推播任務執行完畢。")