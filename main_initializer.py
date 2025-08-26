# main_initializer.py
"""
應用程式啟動時的所有初始化工作。
主要職責：
1. 載入並配置 LINE Bot 的 Rich Menu 別名，讓程式可以根據別名切換不同的選單。
2. 啟動排程器（如果已啟用），處理定時任務，例如每日推播通知。
3. 從外部 JSON 檔案載入 Rich Menu 的 ID，確保即使程式重新啟動，也能使用相同的選單。
"""
import logging
from linebot.v3.messaging import MessagingApi, MessagingApiBlob
from menu_handlers import menu_switcher
from rich_menu_manager import rich_menu_helper

logger = logging.getLogger(__name__)

def initialize(
    line_bot_api: MessagingApi,  line_blob_api: MessagingApiBlob,
    app_config: dict, is_debug_mode: bool, enable_daily_notifications: bool):
    """
    整個應用程式的入口點之一，處理在應用程式啟動時所需的所有初始化服務。
    確保在任何使用者請求被處理之前，所有必要的配置和資源都已準備就緒。
    """
    logger.info("在應用程式啟動時初始化服務...")

    # --- 初始化 menu_switcher 中的別名 ---
    """
    將 Rich Menu 的別名常數傳遞給 menu_switcher 模組。
    讓 menu_switcher 知道每個選單的「名稱」（例如 "MAIN_MENU_ALIAS"），而不是直接依賴於具體的 Rich Menu ID。
    提高程式碼的可讀性和維護性，因為只需要在一個地方修改別名。
    """
    menu_switcher.init_menu_aliases(
        main_alias=app_config["MAIN_MENU_ALIAS"],
        weather_alias=app_config["WEATHER_QUERY_ALIAS"],
        typhoon_alias=app_config["TYPHOON_ZONE_ALIAS"],
        life_alias=app_config["LIFE_REMINDER_ALIAS"],
        settings_alias=app_config["SETTINGS_ALIAS"]
    )
    logger.info("其他處理器已載入。")

    # --- 啟動推播排程器的日誌 ---
    """
    根據環境變數 `enable_daily_notifications` 的設定，決定是否啟動推播排程器。
    在 Cloud Run 等無伺服器環境中，不應該在處理請求的主執行緒中啟動排程器，因為主執行緒只在請求時才存在。
    這裡只是一個日誌記錄，提示需要獨立運行排程器。
    """
    if enable_daily_notifications:
        logger.warning("在雲端環境中，請不要在主執行緒中直接呼叫排程器。")
        logger.info("推播排程器已啟動。(注意：此處僅為日誌記錄，需獨立執行 scheduler.py)")
    else:
        logger.info("推播排程器已禁用。")

    # --- 從 JSON 檔案載入 Rich Menu ID ---
    """
    在應用程式啟動時，將 Rich Menu ID 映射載入到記憶體中。
    確保應用程式在啟動時，能夠快速的從檔案讀取 Rich Menu ID，而不需要在每次啟動時都重新呼叫 LINE API，減少 API 請求次數和啟動時間。
    部署到雲端時，這個 JSON 檔案是由 Dockerfile 腳本在建置階段生成的。
    在本機是由 `rich_menu_deployer.py` 腳本在部署時自動生成的。
    """
    # 呼叫 rich_menu_helper 的函式載入 Rich Menu ID
    rich_menu_data = rich_menu_helper.load_alias_map()

    # 檢查是否成功載入
    if rich_menu_data:
        app_config["RICH_MENU_ALIAS_MAP"].update(rich_menu_data)
        logger.info("已成功從 rich_menu_ids.json 檔案載入 Rich Menu ID 映射。")
    else:
        logger.warning("rich_menu_ids.json 檔案不存在或無法讀取。請先手動執行部署腳本。")

    logger.info("服務初始化已完成。")
    logger.info(f"載入的 Rich Menu ID 映射: {app_config.get('RICH_MENU_ALIAS_MAP')}")