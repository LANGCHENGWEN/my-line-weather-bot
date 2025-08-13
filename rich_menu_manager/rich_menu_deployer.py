# rich_menu_manager/rich_menu_deployer.py
"""
這個檔案是 Rich Menu 的部署腳本，負責將所有在 `rich_menu_configs.py` 中定義的 Rich Menu，自動化的部署到 LINE 平台上。
*** 如果有變更 Rich Menu ，就先在本機直接執行這個檔案，再部署到雲端。
執行流程：
1. 根據運行模式（Debug 或雲端）決定部署策略。
   - 在 Debug 模式下，先刪除所有舊的 Rich Menu，然後重新創建。
   - 在雲端模式下，先檢查現有的 Rich Menu 別名，如果已存在，則嘗試重用；如果不存在，則創建新的。
2. 遍歷 `ALL_RICH_MENU_CONFIGS` 列表中的每一個配置，執行以下步驟：
   - 呼叫 `rich_menu_api_client.py` 中的函式來創建 Rich Menu、上傳圖片，並設定別名。
3. 最後，將主要功能母選單設定為預設 Rich Menu。
4. 部署完成後，將別名與其對應的 Rich Menu ID 儲存到一個 JSON 檔案中，以便後續使用。

這個腳本將部署的過程完全自動化，避免手動操作的繁瑣和出錯的可能性。
"""
import os
import sys

# 讓 config.py 和 utils/api_helper.py 能夠順利導入，都位於根目錄
# 如果沒有這句，在預設情況下這個檔案執行時是會找不到上一層目錄的檔案
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import logging
from linebot.v3.messaging import MessagingApi, MessagingApiBlob

from config import IS_DEBUG_MODE

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
) -> dict:
    """
    Rich Menu 部署的核心入口點，協調整個部署過程。
    根據傳入的參數（例如是否為 Debug 模式），決定是執行完全重新部署，還是進行更新。
    此函式會遍歷所有 Rich Menu 的配置，並依序呼叫底層 API 客戶端的函式來完成創建、上傳圖片和設定別名等步驟。
    最後會設定預設 Rich Menu，並將最終的別名-ID 對照表返回。
    """
    logger.info("正在啟動 Rich Menu 設定部署流程...")

    # --- 處理 Debug 模式與非 Debug 模式的部署邏輯 ---
    """
    根據 `is_debug_mode` 參數來決定 Rich Menu 的部署策略。
    這是一個對於開發與生產環境的優化。
    """
    existing_alias_map = {}
    if not is_debug_mode:
        """
        非 Debug 模式 (生產環境)：
        嘗試獲取現有 Rich Menu 別名對應的 ID。
        如果別名已經存在，就跳過創建和上傳圖片的步驟，直接使用舊的 Rich Menu ID。
        這樣可以節省 API 呼叫次數，加快部署速度，避免因重複創建導致的 LINE 平台資源浪費。
        """
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
        """
        Debug 模式 (開發環境)：
        程式會強制呼叫 `delete_all_rich_menus_on_line` 函式。
        這是為了在開發過程中，當 Rich Menu 的結構或圖片頻繁變動時，能夠確保每次部署都是一個全新的、乾淨的狀態，避免舊的 Rich Menu 殘留導致的混亂。
        """
        logger.debug("正在刪除所有舊的 Rich Menu 並強制重新創建。")
        delete_all_rich_menus_on_line(line_bot_api)

    # --- 遍歷所有 Rich Menu 配置並執行部署流程 ---
    """
    迭代 `all_rich_menu_configs` 列表中的每一個 Rich Menu 配置字典，依序完成創建、圖片上傳、別名設定等步驟。
    這個迴圈是部署流程的核心。
    透過遍歷一個集中配置的列表，程式可以自動化的處理每個 Rich Menu 的部署，而無需為每個 Rich Menu 單獨編寫重複的程式碼。
    包含錯誤處理，確保即使某個 Rich Menu 的部署失敗，也不會影響其他 Rich Menu 的部署。
    這種設計體現了「DRY (Don't Repeat Yourself)」原則，提高程式碼的效率和可維護性。
    """
    created_rich_menu_ids = {}
    for config in all_rich_menu_configs:
        get_menu_obj_func = config['get_menu_obj_func']
        image_path = config['image_path']
        alias = config['alias']
        
        # 檢查圖片檔案是否存在
        if not os.path.exists(image_path):
            logger.error(f"Rich Menu 圖片文件缺失！請確保 {image_path} 存在。跳過 '{alias}'。")
            continue

        # 判斷是否要重複使用已經存在於 LINE 平台上的 Rich Menu，而不是每次都重新建立一個
        reuse_existing = (not is_debug_mode) and (alias in existing_alias_map)
        if reuse_existing:
            rich_menu_id = existing_alias_map[alias]
            logger.info(f"跳過重建 Rich Menu，重用已存在的 ID: {rich_menu_id}。")
        else:
            logger.info(f"正在為別名 '{alias}' 構建並創建 Rich Menu...")

            # 創建 Rich Menu Request 物件
            rich_menu_request_obj = get_menu_obj_func()
            if rich_menu_request_obj:
                rich_menu_id = create_rich_menu_on_line(line_bot_api, rich_menu_request_obj)
            else:
                logger.error(f"無法從函式構建 Rich Menu Request 物件，跳過 '{alias}'。")
                continue # 跳過當前 Rich Menu 的後續處理
        
            # 上傳圖片
            if not upload_rich_menu_image_to_line(line_blob_api, rich_menu_id, image_path):
                logger.error(f"Rich Menu '{alias}' 圖片上傳失敗，可能導致顯示問題。")

            # 創建或更新別名
            if not create_or_update_rich_menu_alias_on_line(line_bot_api, rich_menu_id, alias):
                logger.error(f"Rich Menu 別名 '{alias}' 未能成功創建/更新，可能無法透過別名切換。")
            else:
                created_rich_menu_ids[alias] = rich_menu_id

        # 不論是新建還是舊的 Rich Menu，都會被儲存到 created_rich_menu_ids 這個字典裡
        if reuse_existing:
            created_rich_menu_ids[alias] = existing_alias_map[alias]
            
    # --- 設定 LINE Bot 的預設 Rich Menu ---
    """
    - 功能完整性：每個新加入的好友或沒有綁定特定 Rich Menu 的用戶，都會自動看到這個預設 Rich Menu。
      確保用戶體驗的一致性，並為用戶提供一個清晰的起點。
    - 模組化：從 `created_rich_menu_ids` 字典中，根據 `main_menu_alias` 找到正確的 Rich Menu ID，然後呼叫底層函式來設定它。
      將「設定哪個 Rich Menu 為預設」的邏輯，與「如何設定預設 Rich Menu 」的底層操作分開，保持良好的模組化設計。
    """
    main_menu_actual_id = created_rich_menu_ids.get(main_menu_alias)
    if main_menu_actual_id:
        set_default_rich_menu_on_line(line_bot_api, main_menu_actual_id)
    else:
        logger.error(f"無法找到主選單別名 '{main_menu_alias}' 對應的 Rich Menu ID，無法設定預設。")

    logger.info("Rich Menu 設定部署流程完成。")

    # --- 將部署結果寫入 JSON 檔案 ---
    """
    將部署成功的 Rich Menu 別名與對應的實際 ID 儲存到一個 JSON 檔案中。
    將動態生成的 ID 儲存起來，可以讓其他需要這些 ID 的程式（例如處理 Postback 事件的函式）能夠從檔案中讀取，而不是每次都去呼叫 API 查詢。
    減少對 LINE API 的依賴，加快啟動速度，並為後續的程式碼提供穩定、易於存取的配置。
    """
    try:
        file_path = os.path.join("rich_menu_manager", "rich_menu_ids.json")
        with open(file_path, "w", encoding="utf-8") as fp:
            json.dump(created_rich_menu_ids, fp, ensure_ascii=False, indent=2)
        logger.info(f"Alias → ID 對照表已寫入 {file_path}")
    except Exception as e:
        logger.error(f"寫入 {file_path} 失敗: {e}")

    return created_rich_menu_ids # 返回這個字典

# --- 當有變更 Rich Menu 時，執行以下區塊 ---
if __name__ == "__main__":
    """
    專案部署到雲端前，先在本機執行這個檔案進行 Rich Menu 的部署。
    為了專案部署到雲端時，不會因為部署超時而失敗，所以先在本機執行 Rich Menu 部署。
    這個 `if __name__ == "__main__":` 區塊是 Python 腳本的標準入口點。
    確保只有當 `rich_menu_deployer.py` 檔案被直接執行時，裡面的程式碼才會運行。
    如果這個檔案是作為模組被其他檔案 `import` 進去，這些程式碼就不會被執行。
    這個檔案既可以作為一個獨立的部署工具，也可以作為一個可被其他程式碼導入的模組，提供靈活性。
    """
    # 初始化日誌記錄
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 獲取 LINE API 實例
    line_bot_api, line_blob_api = get_line_bot_apis()

    # 呼叫主要的部署函式 `setup_all_rich_menus`，啟動整個 Rich Menu 的部署流程
    setup_all_rich_menus(
        line_bot_api=line_bot_api,
        line_blob_api=line_blob_api,
        is_debug_mode=IS_DEBUG_MODE,
        all_rich_menu_configs=ALL_RICH_MENU_CONFIGS,
        main_menu_alias=MAIN_MENU_ALIAS
    )

    logging.info("Rich Menu 部署腳本執行完成。")