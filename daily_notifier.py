# daily_notifier.py
# 處理每日自動推播
import time # 用於測試
import logging
import requests # 假設你的 cwa_forecast_api 使用 requests
import schedule

from linebot.v3.messaging import MessagingApi
from linebot.v3.messaging.models import TextMessage

# 從 config 載入設定
from config import (
    CWA_API_KEY, LOCATION_NAME,
    YOUR_LINE_USER_ID, ENABLE_DAILY_NOTIFICATIONS
)

from apscheduler.schedulers.background import BackgroundScheduler # 範例使用 BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger # 新增導入

'''
# 載入預報天氣相關功能 (因為每日推播通常是預報)
from weather_forecast.cwa_forecast_api import get_cwa_forecast_data
from weather_forecast.weather_forecast_parser import parse_forecast_weather
from weather_forecast.line_forecast_messaging import format_forecast_weather_message # 使用預報的格式化
'''

# 載入通用訊息發送功能
from utils.line_common_messaging import ( # 假設您新增了此檔案並同意這樣拆分
    send_line_push_message,
    send_test_notification_setup_message # 導入開發者提示函數
)

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

# 全局變數用於儲存 MessagingApi 實例
_global_line_bot_api_instance = None

def send_daily_weather_notification_to_user(user_id: str, line_bot_api_instance: MessagingApi):
    """
    發送每日天氣預報通知給指定用戶。
    """
    if not user_id:
        logger.warning("嘗試發送每日通知，但用戶 ID 未提供。")
        # send_line_push_message(messaging_api, '你的開發者ID', send_test_notification_setup_message(''))
        return

    logger.info(f"正在為用戶 {user_id} 準備每日天氣通知...")

    # TODO: 從用戶數據中獲取該用戶的預設地點
    # 這裡暫時使用一個硬編碼的地點作為示例
    # 實際應用中，您會從資料庫或 user_state_manager 中獲取用戶設定的地點
    default_county = "臺中市" # 假設用戶的預設縣市
    default_township = "北區" # 假設用戶的預設鄉鎮市區

    try:
        # 獲取天氣預報數據 (仍使用 F-D0047-091)
        weather_data = get_cwa_forecast_data(api_key=CWA_API_KEY, township_name=default_township)

        if not weather_data:
            logger.error(f"無法取得 {default_township} 的預報資料，無法發送每日通知。")
            send_line_push_message(line_bot_api_instance, user_id, TextMessage(text=f"抱歉，無法取得您預設地點 {default_county}{default_township} 的每日天氣通知。"))
            return

        parsed_weather = parse_forecast_weather(weather_data, default_township)

        if parsed_weather and parsed_weather.get('forecast_periods'):
            # 獲取今天的第一個時段的天氣資訊作為摘要
            today_forecast = parsed_weather['forecast_periods'][0] # 取第一個時段作為今日摘要

            weather_desc = today_forecast.get('weather_desc', 'N/A')
            min_temp = today_forecast.get('min_temp', 'N/A')
            max_temp = today_forecast.get('max_temp', 'N/A')
            pop = today_forecast.get('pop', 'N/A')
            comfort_index = today_forecast.get('comfort_index', 'N/A')

            message_text = (
                f"☀️ 早安！您好，這是今日 ({today_forecast.get('forecast_date', 'N/A')}) {default_county}{default_township} 的天氣概況：\n"
                f"☁️ 天氣: {weather_desc}\n"
                f"🌡️ 氣溫: {min_temp}°C ~ {max_temp}°C\n"
                f"☔ 降雨機率: {pop}%\n"
                f"🚶 體感: {comfort_index}\n\n"
                f"祝您有美好的一天！"
            )
            push_message = TextMessage(text=message_text)
            send_line_push_message(line_bot_api_instance, user_id, push_message) # 使用傳入的實例
            logger.info(f"已成功發送每日天氣通知給用戶 {user_id}。")
        else:
            logger.warning(f"解析 {default_township} 天氣預報時數據不完整，無法發送每日通知。")
            send_line_push_message(line_bot_api_instance, user_id, TextMessage(text=f"抱歉，無法取得您預設地點 {default_county}{default_township} 的詳細每日天氣通知。"))

    except Exception as e:
        logger.error(f"為用戶 {user_id} 發送每日通知時發生錯誤: {e}", exc_info=True)
        send_line_push_message(line_bot_api_instance, user_id, TextMessage(text=f"抱歉，發送每日天氣通知時發生錯誤，請稍後再試。"))

def _run_pending_jobs():
    """運行排程中的任務。"""
    if _global_line_bot_api_instance: # 確保有 MessagingApi 實例
        # TODO: 從資料庫或用戶管理模組獲取所有已訂閱每日通知的用戶 ID 列表
        # 這裡僅使用 YOUR_LINE_USER_ID 作為示例
        subscribed_users = [YOUR_LINE_USER_ID] if YOUR_LINE_USER_ID else [] # 確保 YOUR_LINE_USER_ID 有值
        
        for user_id in subscribed_users:
            send_daily_weather_notification(user_id, _global_line_bot_api_instance) # 傳遞實例

        schedule.run_pending()
    else:
        logger.warning("MessagingApi 實例未初始化，無法運行排程任務。")

def start_daily_notifier(line_bot_api_instance: MessagingApi):
    """
    啟動每日天氣通知的排程器。
    """
    global _global_line_bot_api_instance
    _global_line_bot_api_instance = line_bot_api_instance # 將實例儲存到全局變數

    # 清除所有現有排程，防止重複
    schedule.clear()
    
    # 排程每日早上 7:00 發送通知
    schedule.every().day.at("07:00").do(_run_pending_jobs)
    logger.info("每日天氣通知排程器已設置為每日 07:00 執行。")

    # 在獨立線程中運行排程器，不阻塞主線程
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(1) # 每秒檢查一次排程

    import threading
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("每日通知排程器線程已啟動。")

def send_test_notification_setup_message_for_dev(developer_info: str = "") -> str:
    """
    回覆開發者關於測試每日通知設定的訊息。
    """
    message = (
        "請在 config.py 中設定 YOUR_LINE_USER_ID。\n"
        "這是用於測試每日推播通知功能的目標用戶 ID。您可以在 LINE Developers 後台找到您的用戶 ID。"
    )
    if developer_info:
        message += f"\n(開發者訊息: {developer_info})"
    
    logger.warning(message)
    return message