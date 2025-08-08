# main_initializer.py
import os
import json
import logging
from linebot.v3.messaging import MessagingApi, MessagingApiBlob

from menu_handlers import menu_switcher
from utils.api_helper import get_line_bot_apis
# from rich_menu_manager import rich_menu_deployer
# 導入我們自己的排程器模組
# from scheduler import main as run_scheduler

logger = logging.getLogger(__name__)

def initialize(
    line_bot_api: MessagingApi,  line_blob_api: MessagingApiBlob,
    app_config: dict, is_debug_mode: bool, enable_daily_notifications: bool):
    """
    應用程式啟動時的所有初始化服務。
    """
    logger.info("在應用程式啟動時初始化服務...")
    
    # 初始化 menu_switcher 中的別名
    # 從 app_config 中獲取所有別名常數
    menu_switcher.init_menu_aliases(
        main_alias=app_config["MAIN_MENU_ALIAS"],
        weather_alias=app_config["WEATHER_QUERY_ALIAS"], # 假設這些也在 app_config 中，或者在 config.py 中直接引用
        typhoon_alias=app_config["TYPHOON_ZONE_ALIAS"],
        life_alias=app_config["LIFE_REMINDER_ALIAS"],
        settings_alias=app_config["SETTINGS_ALIAS"]
    )
    logger.info("其他處理器已載入。")

    # 將這個全局的 line_bot_api_instance 傳遞給 daily_notifier
    if enable_daily_notifications:
        # run_scheduler(line_bot_api)
        logger.warning("在雲端環境中，請不要在主執行緒中直接呼叫排程器。")
        logger.info("推播排程器已啟動。(注意：此處僅為日誌記錄，需獨立執行 scheduler.py)")
    else:
        logger.info("推播排程器已禁用。")

    # --- 新增的邏輯：從檔案載入 Rich Menu ID ---
    try:
        file_path = os.path.join("rich_menu_manager", "rich_menu_ids.json")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                app_config["RICH_MENU_ALIAS_MAP"].update(json.load(f))
            logger.info("已成功從 rich_menu_ids.json 檔案載入 Rich Menu ID 映射。")
        else:
            logger.warning("rich_menu_ids.json 檔案不存在。請先手動執行部署腳本。")
    except Exception as e:
        logger.error(f"讀取 rich_menu_ids.json 檔案時發生錯誤: {e}")

    logger.info("服務初始化已完成。")
    logger.info(f"載入的 Rich Menu ID 映射: {app_config.get('RICH_MENU_ALIAS_MAP')}")