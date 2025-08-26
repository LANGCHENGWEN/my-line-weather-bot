# scheduler.py
"""
本地端使用的排程器，主要用於在開發階段測試定時推播任務。
使用 Python 的 `schedule` 函式庫來管理和運行排程任務。
注意：這個檔案不應在雲端部署的生產環境中使用。
在雲端環境（如 Google Cloud Run），排程任務會由專門的服務（例如 Cloud Scheduler）透過呼叫 Webhook API 路由來觸發。
***本機測試時，單獨執行這個檔案
"""
import time
import logging
import schedule

from utils.api_helper import get_messaging_api

# 導入推播任務的模組
from push_modules.push_solar_terms import push_solar_terms_notification
from push_modules.push_daily_weather import push_daily_weather_notification
from push_modules.push_weekend_weather import push_weekend_weather_notification
from push_modules.push_typhoon_notification import check_and_push_typhoon_notification

logger = logging.getLogger(__name__)

def main():
    """
    本地排程器的主要運行函式，負責設定日誌、定義所有排程任務，並在一個無限迴圈中持續檢查並執行這些任務。
    在雲端環境中，每個任務通常會被獨立的排程服務觸發，因此這裡的 schedule.run_pending() 主要是為了本地測試。
    """
    # 設定日誌記錄，讓運行資訊能夠被顯示在控制台
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # 從 api_helper.py 取得已經初始化好的 LINE Messaging API 實例
    # 避免在每個推播模組中重複初始化 API
    line_bot_api = get_messaging_api()
    
    # --- 定義排程任務 ---
    """
    使用 `schedule` 函式庫設定各種定時任務。
    `schedule.every()...` 語法用來指定任務執行的頻率和時間。
    `do()` 方法後面跟著要執行的函式，以及傳遞給它的參數。
    `tag()` 方法用來給排程任務一個標籤，方便日後管理或取消特定任務。
    """
    # 每日天氣：每天早上 8 點
    schedule.every().day.at("08:00").do(
        push_daily_weather_notification,
        line_bot_api_instance=line_bot_api
    ).tag('daily_weather')

    # 颱風通知：每小時檢查一次
    schedule.every(1).hour.do(
        check_and_push_typhoon_notification,
        line_bot_api_instance=line_bot_api
    ).tag('typhoon_notification')
    
    # 週末天氣：每週五晚上 7 點
    schedule.every().friday.at("19:00").do(
        push_weekend_weather_notification,
        line_bot_api_instance=line_bot_api
    ).tag('weekend_weather')

    # 節氣小知識：每天早上 7:30，但任務會自行檢查是否為節氣日
    # 確保每天都檢查，但只有在節氣日當天才會發送推播
    schedule.every().day.at("07:30").do(
        push_solar_terms_notification,
        line_bot_api_instance=line_bot_api
    ).tag('solar_terms')
    
    logger.info("排程已啟動。")

    # 這個無限迴圈用於本地測試；在雲端部署時，每個任務會由排程服務獨立觸發，不需要這個迴圈
    """
    `schedule` 函式庫運作的核心。
    `schedule.run_pending()` 會檢查所有已定義的排程任務，並執行那些到期但尚未執行的任務。
    `time.sleep(1)` 讓程式每秒暫停一次，防止 CPU 資源被佔用過高，同時也確保排程檢查是持續且規律進行的。
    """
    while True:
        schedule.run_pending()
        time.sleep(1)

# 當這個檔案被直接執行時，呼叫 main() 函式來啟動排程器
if __name__ == "__main__":
    main()