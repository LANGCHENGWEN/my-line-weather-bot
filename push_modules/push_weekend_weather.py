# push_modules/push_weekend_weather.py
import logging
from datetime import datetime

from utils.line_common_messaging import send_line_push_message
from utils.firestore_manager import get_users_by_city, get_user_push_settings

# 直接從 weekend_handler 模組中導入我們封裝好的函式
from weekend_weather.weekend_handler import create_weekend_weather_message

logger = logging.getLogger(__name__)

# 推播功能的 feature_id
FEATURE_ID = "weekend_weather_push"

def push_weekend_weather_notification(line_bot_api_instance):
    """
    推播週末天氣預報給所有已開啟此功能的用戶。
    """
    # 檢查今天是否為星期五，以確保手動觸發時邏輯正確
    if datetime.now().weekday() != 4: # 4 代表星期五
        logger.info("今天不是星期五，週末天氣推播任務跳過。")
        return

    logger.info("開始執行週末天氣推播任務...")
    
    # 從資料庫獲取所有用戶及其預設城市
    all_users_by_city = get_users_by_city()
    if not all_users_by_city:
        logger.warning("沒有用戶資料，推播任務結束。")
        return

    for city, user_ids in all_users_by_city.items():
        try:
            # 這裡就是關鍵：直接呼叫 create_weekend_weather_message 函式
            messages_to_send = create_weekend_weather_message(city)

            if messages_to_send:
                # 針對每個用戶，檢查他們是否開啟了週末天氣推播
                for user_id in user_ids:
                    try:
                        user_settings = get_user_push_settings(user_id)
                        if user_settings.get(FEATURE_ID):
                            logger.info(f"正在為用戶 {user_id[:8]}... 推播 {city} 的週末天氣。")

                            # 你的推播函式
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
                
        except Exception as e:
            logger.error(f"處理城市 {city} 的週末天氣推播時發生錯誤: {e}", exc_info=True)

    logger.info("週末天氣推播任務執行完畢。")