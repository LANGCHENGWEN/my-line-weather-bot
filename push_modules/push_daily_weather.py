# push_modules/push_daily_weather.py
import logging
from linebot.v3.messaging.models import TextMessage, FlexMessage

from config import CWA_API_KEY
from utils.line_common_messaging import send_line_push_message
# 導入你更完善的資料庫管理模組
from utils.user_data_manager import get_users_by_city, get_user_push_settings

# 導入我們新的數據聚合器
from weather_today.today_weather_aggregator import get_today_all_weather_data

# 導入用來建立 Flex Message 的檔案
from weather_today.today_weather_flex_messages_push import create_daily_weather_flex_message

logger = logging.getLogger(__name__)

# 推播功能的 feature_id
FEATURE_ID = "daily_reminder_push"

def push_daily_weather_notification(line_bot_api_instance):
    """
    推播每日天氣預報給所有已開啟此功能的用戶。
    """
    logger.info("開始執行每日天氣推播任務...")
    
    # 從資料庫獲取所有用戶及其預設城市
    all_users_by_city = get_users_by_city()
    if not all_users_by_city:
        logger.warning("沒有用戶資料，推播任務結束。")
        return

    for city, user_ids in all_users_by_city.items():
        try:
            # 1. 使用數據聚合器取得該城市所有天氣預報數據
            all_weather_data = get_today_all_weather_data(city)
            # 如果聚合器返回 None，代表取得數據時發生嚴重錯誤，直接跳過此城市
            if not all_weather_data:
                logger.error(f"無法為城市 {city} 取得所有天氣數據。跳過此城市的推播。")
                continue

            # 2. 建立 Flex Message
            flex_message_to_send = create_daily_weather_flex_message(
                location=all_weather_data.get("locationName", city),
                parsed_weather=all_weather_data.get("general_forecast", {}),
                parsed_data=all_weather_data.get("hourly_forecast", []),
                parsed_uv_data=all_weather_data.get("uv_data", {})
            )
            
            if not flex_message_to_send:
                logger.error(f"無法為 {city} 產生每日天氣 Flex Message，推播跳過。")
                continue

            # 3. 針對每個用戶，檢查推播設定並發送訊息
            for user_id in user_ids:
                try:
                    user_settings = get_user_push_settings(user_id)
                    if user_settings.get(FEATURE_ID):
                        logger.info(f"正在為用戶 {user_id[:8]}... 推播 {city} 的每日天氣。")

                        # 你的推播函式
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

        except Exception as e:
            logger.error(f"處理城市 {city} 的推播時發生錯誤: {e}", exc_info=True)

    logger.info("每日天氣推播任務執行完畢。")