# push_modules/push_daily_weather.py
"""
執行每日天氣預報的推播任務。
排程系統（如 Cloud Scheduler）會定時觸發。
從資料庫中讀取所有已設定預設城市並開啟每日推播功能的用戶。
針對每個城市，呼叫天氣資料聚合器來獲取完整的天氣數據，然後使用這些數據生成一個美觀且資訊豐富的 Flex Message。
最後，將這個訊息推播給所有屬於該城市的用戶，確保他們每天都能收到最新的天氣資訊。
"""
import logging

from utils.line_common_messaging import send_line_push_message
from utils.firestore_manager import get_users_by_city, get_user_push_settings

# 導入今日天氣的數據聚合器
from weather_today.today_weather_aggregator import get_today_all_weather_data

# 導入今日天氣 Flex Message
from weather_today.today_weather_flex_messages_push import create_daily_weather_flex_message

logger = logging.getLogger(__name__)

# 推播功能的 feature_id
FEATURE_ID = "daily_reminder_push"

# --- 推播每日天氣預報給所有已開啟此功能的用戶 ---
def push_daily_weather_notification(line_bot_api_instance):
    """
    執行流程：
    1. 從資料庫中獲取所有需要推播的用戶，並按城市分組。
    2. 遍歷每個城市，取得該城市最新的綜合天氣數據。
    3. 根據天氣數據，建立一個包含所有必要資訊的 Flex Message 訊息物件。
    4. 針對該城市下的每一位用戶，再次檢查他們是否仍啟用推播功能；如果啟用，則將預先建立好的 Flex Message 推播給該用戶。
    5. 整個過程都會有詳細的日誌記錄，以追蹤任務的執行狀況和潛在錯誤。
    """
    logger.info("開始執行每日天氣推播任務...")
    
    # 1. 從資料庫中批量獲取所有已設定預設城市的用戶
    """
    將用戶按城市分組可以極大的提高效率，而不是為每個用戶單獨查詢一次天氣。
    只需要為每個城市查詢一次天氣數據（`get_today_all_weather_data`），然後將這個天氣數據生成的 Flex Message 重複發送給所有居住在該城市的用戶。
    這種方式減少了對中央氣象署 API 的重複呼叫，也避免重複生成 Flex Message 物件，優化推播任務的性能和成本。
    """
    all_users_by_city = get_users_by_city()
    if not all_users_by_city:
        logger.warning("沒有用戶資料，推播任務結束。")
        return

    for city, user_ids in all_users_by_city.items():
        try:
            # 2. 使用數據聚合器取得該城市所有天氣預報數據
            all_weather_data = get_today_all_weather_data(city)
            # 如果聚合器返回 None，代表取得數據時發生嚴重錯誤，直接跳過此城市
            if not all_weather_data:
                logger.error(f"無法為城市 {city} 取得所有天氣數據。跳過此城市的推播。")
                continue

            # 3. 建立 Flex Message
            flex_message_to_send = create_daily_weather_flex_message(
                location=all_weather_data.get("locationName", city),
                parsed_weather=all_weather_data.get("general_forecast", {}),
                parsed_data=all_weather_data.get("hourly_forecast", []),
                parsed_uv_data=all_weather_data.get("uv_data", {})
            )
            
            if not flex_message_to_send:
                logger.error(f"無法為 {city} 產生每日天氣 Flex Message，推播跳過。")
                continue

            # 4. 為每個用戶發送推播前，再次檢查是否仍啟用推播設定並發送訊息
            """
            雖然 `get_users_by_city` 已經提供了已設定城市的用戶，但用戶隨時可能透過聊天指令關閉推播。
            由於 Firestore 查詢通常有延遲，如果我們依賴一個在推播任務開始時的快照，可能會錯誤的發送訊息給在快照後關閉推播的用戶。
            透過在發送前對每個用戶進行單獨的 `get_user_push_settings` 查詢，可以確保推播決策是基於最新的用戶設定，避免不必要的訊息發送。
            """
            for user_id in user_ids:
                try: # 在發送推播前，會為每個用戶單獨查詢，確認他們是否開啟了 daily_reminder_push
                    user_settings = get_user_push_settings(user_id)
                    if user_settings.get(FEATURE_ID):
                        logger.info(f"正在為用戶 {user_id[:8]}... 推播 {city} 的每日天氣。")

                        # 發送 Flex Message
                        send_line_push_message(
                            line_bot_api_instance=line_bot_api_instance,
                            user_id=user_id,
                            messages=[flex_message_to_send]
                        )

                        logger.info(f"成功為用戶 {user_id[:8]}... 推播 {city} 的每日天氣。")
                    else:
                        logger.debug(f"用戶 {user_id[:8]}... 已關閉每日天氣推播，跳過。")

                except Exception as e:
                    logger.error(f"為用戶 {user_id[:8]}... 推播 {city} 的每日天氣時發生錯誤: {e}", exc_info=True)

        # 5. 處理針對單一城市推播時發生的所有錯誤
        except Exception as e:
            # 確保即使某個城市在獲取天氣數據或處理時發生錯誤，整個推播任務也不會因此中斷
            # 程式會記錄錯誤，然後繼續處理下一個城市，這樣可以最大程度的確保其他城市的用戶仍然能夠收到推播訊息，提高系統的穩定性和可靠性
            logger.error(f"處理城市 {city} 的推播時發生錯誤: {e}", exc_info=True)

    logger.info("每日天氣推播任務執行完畢。")