# app_initializer.py
import logging
from linebot.v3.messaging import MessagingApi # 需要傳入 MessagingApi 實例

from rich_menu_manager import rich_menu_deployer
from menu_handlers import menu_switcher
from daily_notifier import start_daily_notifier # 導入 daily_notifier

logger = logging.getLogger(__name__)

def initialize(global_line_bot_api_instance: MessagingApi, global_rich_menu_api_instance: MessagingApi, app_config: dict, is_debug_mode: bool, enable_daily_notifications: bool, line_channel_access_token: str):
    """
    應用程式啟動時的所有初始化服務。
    包括 Rich Menu 部署、排程器啟動等。
    """
    logger.info("在應用程式啟動時初始化 Rich Menu 和其他服務...")
    
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
        start_daily_notifier(global_line_bot_api_instance)
        logger.info("每日天氣通知排程器已啟動。")
    else:
        logger.info("每日天氣通知排程器已禁用。")

    # 呼叫 Rich Menu 部署器來設定所有 Rich Menu
    # 注意：rich_menu_deployer.setup_all_rich_menus 需要的參數也要傳遞進來
    # 這裡我們將返回的實際 rich menu ID 更新到 app_config 中
    actual_ids = rich_menu_deployer.setup_all_rich_menus(
        line_bot_api=global_line_bot_api_instance,
        rich_menu_api=global_rich_menu_api_instance,
        is_debug_mode=is_debug_mode,
        all_rich_menu_configs=app_config.get("ALL_RICH_MENU_CONFIGS"), # 這些也應該來自 app_config 或 config
        main_menu_alias=app_config["MAIN_MENU_ALIAS"],
        line_channel_access_token=line_channel_access_token
    )
    app_config["RICH_MENU_ALIAS_MAP"].update(actual_ids) # 更新到 app_config 中的實際 ID 映射

    logger.info("Rich Menu 部署和服務初始化已完成。")
    logger.info(f"實際部署的 Rich Menu ID 映射: {app_config['RICH_MENU_ALIAS_MAP']}")