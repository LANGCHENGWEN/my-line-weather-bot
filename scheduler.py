# scheduler.py
import os
import time
import logging
import schedule

# 從你的共用模組導入 LINE Bot API 實例
from utils.api_helper import get_messaging_api

# 導入推播任務模組和用戶資料庫
from push_modules.push_daily_weather import push_daily_weather_notification
from push_modules.push_weekend_weather import push_weekend_weather_notification
from push_modules.push_solar_terms import push_solar_terms_notification
# 颱風通知模組需要一個定時檢查機制，在下面會解釋
# from push_modules.push_typhoon_notification import check_and_push_typhoon_notification

logger = logging.getLogger(__name__)

def main():
    """
    主要排程運行函式。
    在雲端環境中，每個任務通常會被獨立的排程服務觸發，
    因此這裡的 schedule.run_pending() 主要是為了本地測試。
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # 從 api_helper.py 取得已經初始化好的 LINE Messaging API 實例
    line_bot_api = get_messaging_api()
    
    # --- 定義排程任務 ---
    # 每日天氣：每天早上 8 點
    schedule.every().day.at("08:00").do(
        push_daily_weather_notification,
        line_bot_api_instance=line_bot_api
    ).tag('daily_weather')
    
    # 週末天氣：每週五晚上 7 點
    schedule.every().friday.at("19:00").do(
        push_weekend_weather_notification,
        line_bot_api_instance=line_bot_api
    ).tag('weekend_weather')

    # 節氣小知識：每天早上 7:30，但任務會自行檢查是否為節氣日
    schedule.every().day.at("07:30").do(
        push_solar_terms_notification,
        line_bot_api_instance=line_bot_api
    ).tag('solar_terms')
    
    logger.info("排程已啟動。")

    # 這個無限迴圈用於本地測試。在雲端部署時，
    # 每個任務會由排程服務獨立觸發，不需要這個迴圈。
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()