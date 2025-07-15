# rich_menu_manager/rich_menu_deployer.py
import os
import json
import logging
from linebot.v3.messaging import MessagingApi

# 導入內部模組
from rich_menu_manager import rich_menu_builder
from rich_menu_manager import rich_menu_api_client

logger = logging.getLogger(__name__)

def setup_all_rich_menus(
    line_bot_api: MessagingApi, rich_menu_api: MessagingApi,
    is_debug_mode: bool, all_rich_menu_configs: list,
    main_menu_alias: str, line_channel_access_token: str # <--- 新增此參數，用於傳遞給圖片上傳函式
) -> dict:
    """
    設定並管理所有 Rich Menu，包括主選單和子選單，以及其別名。
    根據 debug 模式決定部署策略。
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
        logger.info("DEBUG 模式：正在刪除所有舊的 Rich Menu 並強制重新創建。")
        rich_menu_api_client.delete_all_rich_menus_on_line(line_bot_api)

    created_rich_menu_ids = {} # 儲存 {alias: rich_menu_id}

    for config in all_rich_menu_configs:
        json_path = config['json_path']
        image_path = config['image_path']
        alias = config['alias']
        
        if not os.path.exists(json_path):
            logger.error(f"Rich Menu JSON 文件缺失！請確保 {json_path} 存在。跳過 '{alias}'。")
            continue
        if not os.path.exists(image_path):
            logger.error(f"Rich Menu 圖片文件缺失！請確保 {image_path} 存在。跳過 '{alias}'。")
            continue

        reuse_existing = (not is_debug_mode) and (alias in existing_alias_map)
        
        if reuse_existing:
            rich_menu_id = existing_alias_map[alias]
            logger.info(f"跳過重建 Rich Menu，重用已存在的 ID: {rich_menu_id}。")
        else:
            logger.info(f"正在為別名 '{alias}' 構建並創建 Rich Menu...")
            rich_menu_request_obj = rich_menu_builder.build_rich_menu_request_from_json(json_path)
            if rich_menu_request_obj:
                rich_menu_id = rich_menu_api_client.create_rich_menu_on_line(line_bot_api, rich_menu_request_obj)
            else:
                logger.error(f"無法從 JSON 構建 Rich Menu Request 物件，跳過 '{alias}'。")
                continue # 跳過當前 Rich Menu 的後續處理
        
            if not rich_menu_api_client.upload_rich_menu_image_to_line(rich_menu_id, image_path, line_channel_access_token):
                logger.error(f"Rich Menu '{alias}' 圖片上傳失敗，可能導致顯示問題。")

            if not rich_menu_api_client.create_or_update_rich_menu_alias_on_line(line_bot_api, rich_menu_id, alias):
                logger.error(f"Rich Menu 別名 '{alias}' 未能成功創建/更新，可能無法透過別名切換。")
            else:
                created_rich_menu_ids[alias] = rich_menu_id

        if reuse_existing:
            created_rich_menu_ids[alias] = existing_alias_map[alias]
            
    # 設定預設 Rich Menu
    main_menu_actual_id = created_rich_menu_ids.get(main_menu_alias)
    if main_menu_actual_id:
        rich_menu_api_client.set_default_rich_menu_on_line(line_bot_api, main_menu_actual_id)
    else:
        logger.error(f"無法找到主選單別名 '{main_menu_alias}' 對應的 Rich Menu ID，無法設定預設。")

    logger.info("Rich Menu 設定部署流程完成。")

    # === NEW: 把 alias→ID 存成 JSON，供應用程式讀取 ===
    try:
        with open("rich_menu_ids.json", "w", encoding="utf-8") as fp:
            json.dump(created_rich_menu_ids, fp, ensure_ascii=False, indent=2)
        logger.info("Alias→ID 對照表已寫入 rich_menu_ids.json")
    except Exception as e:
        logger.error(f"寫入 rich_menu_ids.json 失敗: {e}")

    return created_rich_menu_ids # <-- 返回這個字典