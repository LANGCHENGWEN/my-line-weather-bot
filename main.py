# main.py
"""
整個 LINE Bot 專案的主入口檔案。
使用 Flask 框架建立一個 Web 伺服器，並處理所有來自 LINE 的 Webhook 事件。
主要職責：
1. 建立 Flask 應用程式和 LINE SDK 實例。
2. 設定 Webhook 路徑，將接收到的 LINE 事件分發給不同的處理模組。
3. 執行應用程式啟動時的初始化工作，例如載入 Rich Menu ID。
4. 提供多個 API 端點，供外部排程器 (如 Cloud Scheduler) 呼叫，以執行定時推播任務。
"""
import os
import logging
from flask import Flask, request, abort
from importlib import import_module

from linebot.v3.webhook import WebhookHandler
from linebot.v3.webhooks.models import (
    MessageEvent, TextMessageContent,
    PostbackEvent, FollowEvent, UnfollowEvent
)

# 專案共用設定
from utils.api_helper import get_line_bot_apis
from config import LINE_CHANNEL_SECRET, IS_DEBUG_MODE, ENABLE_DAILY_NOTIFICATIONS

# Rich Menu 別名常數
from rich_menu_manager.rich_menu_configs import (
    MAIN_MENU_ALIAS, WEATHER_QUERY_ALIAS,
    TYPHOON_ZONE_ALIAS, LIFE_REMINDER_ALIAS,
    SETTINGS_ALIAS, ALL_RICH_MENU_CONFIGS
)

# 導入初始化函式
from main_initializer import initialize

# 導入推播任務的模組，這些函式由 Cloud Scheduler 觸發
from push_modules.push_solar_terms import push_solar_terms_notification
from push_modules.push_daily_weather import push_daily_weather_notification
from push_modules.push_weekend_weather import push_weekend_weather_notification
from push_modules.push_typhoon_notification import check_and_push_typhoon_notification

# 設定日誌系統，確保所有日誌都輸出到控制台
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logger.info("程式開始啟動...")

# --- 初始化 LINE SDK 和 Flask ---
"""
建立 WebhookHandler 和 Flask 應用程式的實例。
這兩個物件是整個 LINE Bot 運作的基礎。
使用 try-except 區塊捕捉任何初始化時可能發生的錯誤；如果發生錯誤，程式會終止並提供詳細的錯誤訊息。
"""
try:
    handler = WebhookHandler(LINE_CHANNEL_SECRET)
    app = Flask(__name__)
    logger.info("LINE SDK 和 Flask App 實例化成功。")
except Exception as e:
    logger.error("初始化 LINE SDK 或 Flask App 時發生錯誤。", exc_info=True)
    exit(1) # 終止程式，因為啟動已失敗

# --- 健康檢查路由 ---
"""
雲端服務（例如 Cloud Run）會定期呼叫這個端點來確認應用程式是否正常運行。
如果應用程式能夠成功響應 "OK"，代表服務是健康的。
"""
@app.route("/health")
def health_check():
    return "OK", 200

# --- 綁定 LINE 事件 ---
"""
將來自 LINE 的不同事件類型（例如文字訊息、追蹤、回傳資料）導向到對應的處理模組。
使用 `import_module` 動態導入模組，而不是在檔案開頭全部導入，這樣可以延遲加載，讓主檔案更輕量，啟動更快。
"""
# 處理文字訊息事件，將其路由到 handlers.text_router 模組的 handle 函式
@handler.add(MessageEvent, message=TextMessageContent)
def on_text(event):
    import_module("handlers.text_router").handle(event)

# 處理用戶追蹤機器人事件，將其路由到 handlers.follow 模組的 handle 函式
@handler.add(FollowEvent)
def on_follow(event):
    import_module("handlers.follow").handle(event)
    logger.info(f"用戶 {event.source.user_id} 追蹤了機器人。")

# 處理用戶解除追蹤事件，這裡只簡單的記錄日誌，沒有複雜的處理邏輯
@handler.add(UnfollowEvent)
def handle_unfollow(event):
    logger.info(f"用戶 {event.source.user_id} 解除了追蹤。")

# 處理用戶點擊 Rich Menu 或模板訊息按鈕後傳送的 Postback 事件，將其路由到 handlers.postback_router 模組的 handle 函式
@handler.add(PostbackEvent)
def on_postback(event):
    import_module("handlers.postback_router").handle(event)

# --- Flask Webhook ---
"""
LINE Webhook 的主要入口。
LINE 會向這個 URL 發送所有用戶互動事件。
這個函式會驗證請求的簽名（Signature），確保它來自 LINE 官方，然後將請求主體傳遞給 `handler` 進行處理。
"""
@app.route("/callback", methods=["POST"])
def callback():
    sig  = request.headers.get("X-Line-Signature", "") # 從 HTTP Headers 獲取簽名
    body = request.get_data(as_text=True)              # 獲取請求主體，轉成文字格式
    
    # 執行 handler 的 handle 函式來分發事件
    try:
        handler.handle(body, sig)
    except Exception as e:
        logger.error("Webhook 處理錯誤。", exc_info=True)
        abort(400) # 如果簽名無效或其他錯誤，返回 400 錯誤代碼
    return "OK"

# --- 準備初始化用的共用物件 ---
"""
在應用程式啟動時執行，準備 LINE API 的實例和應用程式配置。
這些物件會傳遞給初始化函式 `initialize()` 使用。
"""
logger.info("開始準備初始化用的共用物件...")
try:
    # 建立 LINE Bot 和 Blob API 的實例
    line_bot_api_instance, line_blob_api_instance = get_line_bot_apis()
    logger.info("LINE API 實例化成功。")
except Exception as e:
    logger.error("初始化 LINE API 實例時發生錯誤。", exc_info=True)
    exit(1) # 如果 API 實例化失敗，程式無法正常運行，終止程式

# 集中管理所有應用程式配置的字典
APP_CONFIG = {
    "MAIN_MENU_ALIAS"       : MAIN_MENU_ALIAS,
    "WEATHER_QUERY_ALIAS"   : WEATHER_QUERY_ALIAS,
    "TYPHOON_ZONE_ALIAS"    : TYPHOON_ZONE_ALIAS,
    "LIFE_REMINDER_ALIAS"   : LIFE_REMINDER_ALIAS,
    "SETTINGS_ALIAS"        : SETTINGS_ALIAS,
    "ALL_RICH_MENU_CONFIGS" : ALL_RICH_MENU_CONFIGS, # Rich Menu 設定的中央配置中心
    "RICH_MENU_ALIAS_MAP"   : {}                     # initialize() 會寫入實際的 Rich Menu ID
}
logger.info("APP_CONFIG 設定完成。")

# --- 執行專案啟動初始化 ---
"""
呼叫 `main_initializer.py` 中的 `initialize()` 函式，執行所有在應用程式啟動前必須完成的任務，例如載入 Rich Menu ID。
"""
logger.info("執行專案啟動初始化...")
try:
    initialize(
        line_bot_api=line_bot_api_instance,
        line_blob_api=line_blob_api_instance,
        app_config=APP_CONFIG,
        is_debug_mode=IS_DEBUG_MODE,
        enable_daily_notifications=ENABLE_DAILY_NOTIFICATIONS
    )
    logger.info("專案初始化完成。")
except Exception as e:
    logger.error("執行 initialize() 函式時發生錯誤。", exc_info=True)
    exit(1)

# --- Cloud Scheduler 觸發的推播路由 ---
"""
這些路由專門設計給外部排程服務（例如 Google Cloud Scheduler）呼叫。
當 Cloud Scheduler 定時發送 HTTP 請求到這些 URL 時，會觸發對應的推播任務。
"""
# 由 Cloud Scheduler 定時觸發，執行每日天氣推播任務
# 呼叫 `push_daily_weather_notification` 函式，向用戶推播每日天氣預報
@app.route("/push_daily_weather", methods=["GET"])
def push_daily_weather():
    try:
        logger.info("Cloud Scheduler 觸發每日天氣推播任務。")
        push_daily_weather_notification(line_bot_api_instance=line_bot_api_instance)
        return "每日天氣推播成功。", 200
    except Exception as e:
        logger.error("每日天氣推播任務執行失敗。", exc_info=True)
        return f"每日天氣推播出現錯誤: {str(e)}", 500

# 由 Cloud Scheduler 定時觸發，執行節氣推播任務
# 呼叫 `push_solar_terms_notification` 函式，向用戶推播節氣通知
@app.route("/push_solar_terms", methods=["GET"])
def push_solar_terms():
    try:
        logger.info("Cloud Scheduler 觸發節氣推播任務。")
        push_solar_terms_notification(line_bot_api_instance=line_bot_api_instance)
        return "節氣推播成功。", 200
    except Exception as e:
        logger.error("節氣推播任務執行失敗。", exc_info=True)
        return f"節氣推播出現錯誤: {str(e)}", 500

# 由 Cloud Scheduler 定時觸發，執行颱風推播任務
# 呼叫 `check_and_push_typhoon_notification` 函式，檢查是否有颱風警報並推播給用戶
@app.route("/push_typhoon_notification", methods=["GET"])
def push_typhoon_notification():
    try:
        logger.info("Cloud Scheduler 觸發颱風推播任務。")
        check_and_push_typhoon_notification(line_bot_api_instance=line_bot_api_instance)
        return "颱風推播成功。", 200
    except Exception as e:
        logger.error("颱風推播任務執行失敗。", exc_info=True)
        return f"颱風推播出現錯誤: {str(e)}", 500

# 由 Cloud Scheduler 定時觸發，執行週末天氣推播任務
# 呼叫 `push_weekend_weather_notification` 函式，向用戶推播週末天氣預報
@app.route("/push_weekend_weather", methods=["GET"])
def push_weekend_weather():
    try:
        logger.info("Cloud Scheduler 觸發週末天氣推播任務。")
        push_weekend_weather_notification(line_bot_api_instance=line_bot_api_instance)
        return "週末天氣推播成功。", 200
    except Exception as e:
        logger.error("週末天氣推播任務執行失敗。", exc_info=True)
        return f"週末天氣推播出現錯誤: {str(e)}", 500

# --- 啟動 Flask ---
# 本機測試才用 Flask，部署到雲端用 gunicorn 伺服器
# 在本地環境中直接運行 Flask 應用程式
# `if __name__ == "__main__":` 確保這段程式碼只在檔案被直接執行時才會運行，而不是在被其他模組導入時運行
# 在雲端部署時，`gunicorn` 會負責啟動應用程式，所以這段程式碼不會被執行

if __name__ == "__main__":
    # 先從環境變數讀 PORT，沒有設定就用預設的 5000
    port = int(os.environ.get("PORT", 5000))
    # 啟動應用程式，監聽所有網路接口 (0.0.0.0)
    app.run(host='0.0.0.0', port=port, debug=True)
