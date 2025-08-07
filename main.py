# main.py －－ Flask + LINE Webhook 入口
# 這是整個 Line Bot 的入口檔案
# main.py  —— 入口＋Adapter（Flask + LINE SDK）
import os
import logging
import traceback
from flask import Flask, request, abort
from importlib import import_module

from linebot.v3.webhook import WebhookHandler
from linebot.v3.webhooks.models import (
    MessageEvent, TextMessageContent,
    FollowEvent, PostbackEvent, UnfollowEvent
)

# --- 專案共用設定 ---
from utils.api_helper import get_line_bot_apis
from config import (
    LINE_CHANNEL_SECRET, IS_DEBUG_MODE, ENABLE_DAILY_NOTIFICATIONS
)

# Rich‑menu 別名常數
from rich_menu_manager.rich_menu_configs import (
    MAIN_MENU_ALIAS, WEATHER_QUERY_ALIAS,
    TYPHOON_ZONE_ALIAS, LIFE_REMINDER_ALIAS,
    SETTINGS_ALIAS, ALL_RICH_MENU_CONFIGS
)

from main_initializer import initialize

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logger.info("程式開始啟動...")

# --- 初始化 SDK ---
try:
    handler = WebhookHandler(LINE_CHANNEL_SECRET)
    app = Flask(__name__)
    logger.info("LINE SDK 和 Flask App 實例化成功。")
except Exception as e:
    logger.error("初始化 LINE SDK 或 Flask App 時發生錯誤。", exc_info=True)
    # 在此處可以選擇中止程式，因為啟動已失敗
    exit(1)

# 新增健康檢查路由
@app.route("/health")
def health_check():
    return "OK", 200

# --- 綁定事件 ---
@handler.add(MessageEvent, message=TextMessageContent)
def on_text(event):
    import_module("handlers.text_router").handle(event)

@handler.add(FollowEvent)
def on_follow(event):
    import_module("handlers.follow").handle(event)
    logger.info(f"使用者 {event.source.user_id} 追蹤了機器人。")

@handler.add(UnfollowEvent)
def handle_unfollow(event):
    logger.info(f"使用者 {event.source.user_id} 解除了追蹤。")

@handler.add(PostbackEvent)
def on_postback(event):
    import_module("handlers.postback_router").handle(event)

# --- Flask webhook ---
@app.route("/callback", methods=["POST"])
def callback():
    sig  = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, sig)
    except Exception as e:
        logger.error("Webhook 處理錯誤。", exc_info=True)
        abort(400)
    return "OK"

# --- 準備初始化用的共用物件 ---
# 供 Rich‑menu 部署、排程等啟動邏輯使用
logger.info("開始準備初始化用的共用物件...")
try:
    line_bot_api_instance, line_blob_api_instance = get_line_bot_apis()
    logger.info("LINE API 實例化成功。")
except Exception as e:
    logger.error("初始化 LINE API 實例時發生錯誤。", exc_info=True)
    exit(1)

# app_config 供 initialize() 用（可依實際專案再加欄位）
APP_CONFIG = {
    "MAIN_MENU_ALIAS":      MAIN_MENU_ALIAS,
    "WEATHER_QUERY_ALIAS":  WEATHER_QUERY_ALIAS,
    "TYPHOON_ZONE_ALIAS":   TYPHOON_ZONE_ALIAS,
    "LIFE_REMINDER_ALIAS":  LIFE_REMINDER_ALIAS,
    "SETTINGS_ALIAS":       SETTINGS_ALIAS,
    "ALL_RICH_MENU_CONFIGS": ALL_RICH_MENU_CONFIGS,  # <- 你的 rich‑menu JSON + 圖片清單
    "RICH_MENU_ALIAS_MAP":  {}        # initialize() 會寫入實際 ID
}
logger.info("APP_CONFIG 設定完成。")

# --- 執行專案啟動初始化 ---
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

# --- 啟動 Flask ---
"""
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # 先從環境變數讀 PORT，沒設定就用 5000
    app.run(host='0.0.0.0', port=port, debug=True)
"""