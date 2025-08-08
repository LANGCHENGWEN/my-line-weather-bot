# rich_menu_manager/rich_menu_deployer.py
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import logging
from linebot.v3.messaging import MessagingApi, MessagingApiBlob

from config import IS_DEBUG_MODE, LINE_CHANNEL_ACCESS_TOKEN

from utils.api_helper import get_line_bot_apis

from rich_menu_manager.rich_menu_configs import MAIN_MENU_ALIAS, ALL_RICH_MENU_CONFIGS

from rich_menu_manager.rich_menu_api_client import (
    create_rich_menu_on_line, upload_rich_menu_image_to_line,
    create_or_update_rich_menu_alias_on_line,
    set_default_rich_menu_on_line, delete_all_rich_menus_on_line
)

logger = logging.getLogger(__name__)

def setup_all_rich_menus(
    line_bot_api: MessagingApi, line_blob_api: MessagingApiBlob,
    is_debug_mode: bool, all_rich_menu_configs: list, main_menu_alias: str
    # line_channel_access_token: str # <--- 新增此參數，用於傳遞給圖片上傳函式
) -> dict:
    """
    設定並管理所有 Rich Menu，包括主選單和子選單，以及其別名。
    根據 debug 模式決定部署策略。
    這是獨立的部署腳本。
    """
    logger.info("正在啟動 Rich Menu 設定部署流程...")

    existing_alias_map = {}
    if not is_debug_mode:
        # 非 DEBUG 模式：先抓取現有 alias 對應的 ID，避免不必要重建
        try:
            for config in all_rich_menu_configs:
                alias = config['alias']
                try:
                    alias_info = line_bot_api.get_rich_menu_alias(alias)
                    existing_alias_map[alias] = alias_info.rich_menu_id
                    logger.info(f"已存在 Rich Menu 別名 '{alias}'，ID: {alias_info.rich_menu_id}")
                except Exception as e:
                    if "alias not found" in str(e).lower() or "404" in str(e).lower():
                        logger.info(f"別名 '{alias}' 不存在，將建立新 Rich Menu。")
                    else:
                        logger.warning(f"查詢別名 '{alias}' 發生錯誤：{e}，將嘗試建立。")
        except Exception as e:
            logger.warning(f"擷取現有 Rich Menu alias 對照表失敗: {e}")
    else:
        logger.debug("正在刪除所有舊的 Rich Menu 並強制重新創建。")
        delete_all_rich_menus_on_line(line_bot_api)

    created_rich_menu_ids = {} # 儲存 {alias: rich_menu_id}
    for config in all_rich_menu_configs:
        get_menu_obj_func = config['get_menu_obj_func']
        image_path = config['image_path']
        alias = config['alias']
        
        if not os.path.exists(image_path):
            logger.error(f"Rich Menu 圖片文件缺失！請確保 {image_path} 存在。跳過 '{alias}'。")
            continue

        reuse_existing = (not is_debug_mode) and (alias in existing_alias_map)
        
        if reuse_existing:
            rich_menu_id = existing_alias_map[alias]
            logger.info(f"跳過重建 Rich Menu，重用已存在的 ID: {rich_menu_id}。")
        else:
            logger.info(f"正在為別名 '{alias}' 構建並創建 Rich Menu...")

            rich_menu_request_obj = get_menu_obj_func()
            if rich_menu_request_obj:
                rich_menu_id = create_rich_menu_on_line(line_bot_api, rich_menu_request_obj)
            else:
                logger.error(f"無法從函數構建 Rich Menu Request 物件，跳過 '{alias}'。")
                continue # 跳過當前 Rich Menu 的後續處理
        
            if not upload_rich_menu_image_to_line(line_blob_api, rich_menu_id, image_path):
                logger.error(f"Rich Menu '{alias}' 圖片上傳失敗，可能導致顯示問題。")

            # 創建或更新別名
            if not create_or_update_rich_menu_alias_on_line(line_bot_api, rich_menu_id, alias):
                logger.error(f"Rich Menu 別名 '{alias}' 未能成功創建/更新，可能無法透過別名切換。")
            else:
                created_rich_menu_ids[alias] = rich_menu_id

        if reuse_existing:
            created_rich_menu_ids[alias] = existing_alias_map[alias]
            
    # 設定預設 Rich Menu
    main_menu_actual_id = created_rich_menu_ids.get(main_menu_alias)
    if main_menu_actual_id:
        set_default_rich_menu_on_line(line_bot_api, main_menu_actual_id)
    else:
        logger.error(f"無法找到主選單別名 '{main_menu_alias}' 對應的 Rich Menu ID，無法設定預設。")

    logger.info("Rich Menu 設定部署流程完成。")
    try:
        file_path = os.path.join("rich_menu_manager", "rich_menu_ids.json")
        with open(file_path, "w", encoding="utf-8") as fp:
            json.dump(created_rich_menu_ids, fp, ensure_ascii=False, indent=2)
        logger.info(f"Alias→ID 對照表已寫入 {file_path}")
    except Exception as e:
        logger.error(f"寫入 {file_path} 失敗: {e}")

    return created_rich_menu_ids # <-- 返回這個字典

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    line_bot_api, line_blob_api = get_line_bot_apis(LINE_CHANNEL_ACCESS_TOKEN)

    # 呼叫 Rich Menu 部署器來設定所有 Rich Menu
    # 注意：rich_menu_deployer.setup_all_rich_menus 需要的參數也要傳遞進來
    # 這裡我們將返回的實際 rich menu ID 更新到 app_config 中
    # 執行 Rich Menu 部署腳本
    setup_all_rich_menus(
        line_bot_api=line_bot_api,
        line_blob_api=line_blob_api,
        is_debug_mode=IS_DEBUG_MODE,
        all_rich_menu_configs=ALL_RICH_MENU_CONFIGS, # 這些也應該來自 app_config 或 config
        main_menu_alias=MAIN_MENU_ALIAS
    )

    logging.info("Rich Menu 部署腳本執行完成。")

    