# menu_handlers/menu_switcher.py
"""
這個檔案的主要職責是管理和執行 LINE Bot 的 Rich Menu（圖文選單）切換。
根據用戶傳送的特定指令（通常是文字訊息或 Postback 事件），動態將用戶目前的 Rich Menu 變更為另一個預設好的選單。
"""
import logging
from typing import Optional
from linebot.v3.messaging import MessagingApi
from linebot.v3.webhooks.models import MessageEvent
from linebot.v3.exceptions import InvalidSignatureError

from .menu_reply import build_text_reply
from rich_menu_manager.rich_menu_helper import get_rich_menu_id

# 從 rich_menu_configs.py 匯入 Rich Menu 別名常數
from rich_menu_manager.rich_menu_configs import (
    MAIN_MENU_ALIAS, WEATHER_QUERY_ALIAS,
    TYPHOON_ZONE_ALIAS, LIFE_REMINDER_ALIAS, SETTINGS_ALIAS
)

logger = logging.getLogger(__name__)

# --- 可注入的別名表 ---
"""
這個全域變數用來儲存 Rich Menu 別名與其對應的實際 ID。
使用字典儲存映射關係，可以讓程式碼更具彈性。
函式 `init_menu_aliases` 可以在程式啟動時，從設定檔或 LINE API 取得最新的 Rich Menu ID。
之後整個模組都可以透過這個字典來查找和使用這些 ID，而不需要將 ID 硬編碼在程式中，方便未來的維護和更新。
"""
_alias_map = {
    "main"     : MAIN_MENU_ALIAS,
    "weather"  : WEATHER_QUERY_ALIAS,
    "typhoon"  : TYPHOON_ZONE_ALIAS,
    "life"     : LIFE_REMINDER_ALIAS,
    "settings" : SETTINGS_ALIAS
}

# --- 初始化 Rich Menu 別名映射表的函式 ---
def init_menu_aliases(main_alias, weather_alias, typhoon_alias, life_alias, settings_alias):
    """
    在應用程式啟動時，將外部設定的 Rich Menu 別名，注入到本模組的 `_alias_map` 字典中，供後續的 handle_menu_switching 選單切換函式使用。
    """
    global _alias_map
    _alias_map = {
        "main"     : main_alias,
        "weather"  : weather_alias,
        "typhoon"  : typhoon_alias,
        "life"     : life_alias,
        "settings" : settings_alias
    }
    logger.info(f"menu_switcher: _alias_map 已初始化 → {_alias_map}")

# --- 私有輔助函式：用於根據 Rich Menu 的別名來獲取 ID 並將選單綁定給指定的用戶 ---
def _link_rich_menu_by_alias(line_bot_api: MessagingApi, user_id: str, alias_id: str) -> bool:
    """
    此函式會先嘗試從本地的 JSON 檔案中獲取 Rich Menu ID，如果找不到，才會呼叫 LINE API 獲取。
    這種設計可以減少對 LINE API 的頻繁呼叫，提高效率。
    函式也包含了錯誤處理機制，確保即使綁定失敗，也不會導致程式崩潰。
    """
    try:
        # 1. 先嘗試從本地 JSON 取得 ID
        # 先檢查本地的 `rich_menu_ids.json` 檔案是否有 Rich Menu ID，如果有，就直接使用，避免不必要的 API 呼叫
        rich_menu_id = get_rich_menu_id(alias_id)

        # 2. 若 JSON 取不到，再呼叫 LINE API 來獲取 ID（避免第一次啟動沒有 JSON）
        if not rich_menu_id:
            alias_info = line_bot_api.get_rich_menu_alias(alias_id)
            rich_menu_id = alias_info.rich_menu_id
            logger.warning(f"從 LINE API 取得 Rich Menu ID '{rich_menu_id}' (別名 '{alias_id}')，請確保 rich_menu_ids.json 已更新。")

        # 3. 使用獲取到的 Rich Menu ID 綁定給用戶
        line_bot_api.link_rich_menu_id_to_user(user_id, rich_menu_id)
        logger.info(f"成功將 Rich Menu ID '{rich_menu_id}' (來自別名 '{alias_id}') 綁定給用戶 '{user_id}'。")
        return True
    except InvalidSignatureError as e:
        logger.error(f"LINE API 錯誤：無法綁定 '{alias_id}' -> {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"未知錯誤：綁定 '{alias_id}' 失敗 -> {e}", exc_info=True)
        return False

# --- 供 Postback 路由器使用的公開函式，用於直接根據 Rich Menu 別名來切換選單 ---
def switch_to_alias(api, user_id: str, alias: Optional[str]) -> bool:
    """
    Postback 事件通常只負責切換 Rich Menu，而不需要額外發送回覆訊息。
    這個函式將切換選單的邏輯與回覆訊息的邏輯分離，使程式碼更清晰。
    """
    if not alias:
        logger.warning("switch_to_alias：alias 是空的")
        return False # 如果別名是空的，直接返回 False
    
    ok = _link_rich_menu_by_alias(api, user_id, alias)
    if ok:
        logger.info(f"[RichMenu] user {user_id} → {alias}")
    return ok

# --- 文字訊息的選單切換處理函式，用於根據用戶輸入的文字來切換 Rich Menu ---
def handle_menu_switching(event: MessageEvent, line_bot_api: MessagingApi) -> bool:
    """
    提供用戶另一種方式來導航選單，除了點擊按鈕之外，也可以直接輸入文字指令。
    處理流程：檢查訊息類型 -> 檢查是否有匹配的選單文字 -> 切換選單 -> 回覆確認訊息。
    """
    # 1. 檢查訊息類型
    if not hasattr(event, 'message') or not hasattr(event.message, 'text'):
        return False # 如果不是文字訊息，不處理選單切換

    text = event.message.text
    user_id = event.source.user_id
    reply_token = event.reply_token

    menu_switch_map = {
        "天氣查詢" : _alias_map.get("weather"),
        "颱風專區" : _alias_map.get("typhoon"),
        "生活提醒" : _alias_map.get("life"),
        "設定" : _alias_map.get("settings")
    }

    # 檢查事件是否為文字訊息，然後根據 `menu_switch_map` 字典將文字訊息（例如「天氣查詢」）對應到 Rich Menu 的別名
    if text in menu_switch_map:
        # 2. 檢查是否有匹配的選單文字
        target_alias = menu_switch_map[text]
        logger.info(f"嘗試切換到 '{text}' 選單 (別名: {target_alias})，用戶: {user_id}")

        if _link_rich_menu_by_alias(line_bot_api, user_id, target_alias):
            # 3. 切換選單
            reply_text =f"已切換至 {text} 選單。"

            try:
                # 4. 回覆確認訊息
                reply_req = build_text_reply(reply_text, reply_token)
                line_bot_api.reply_message(reply_req)
                logger.info(f"成功回覆用戶 '{user_id}' 訊息：{reply_text}")
                return True # 成功切換後，會發送一則回覆訊息確認切換成功
            except Exception as e:
                logger.error(f"回覆用戶訊息失敗: {e}", exc_info=True)
                # 如果回覆失敗，這裡不應該再嘗試回覆，避免無限循環或再次報錯
        else:
            # 切換選單失敗時的回覆
            try:
                error_req = build_text_reply("切換選單失敗，請稍候再試。", reply_token)
                line_bot_api.reply_message(error_req)
                logger.info(f"成功回覆用戶 '{user_id}' 錯誤訊息：{error_req}")
            except Exception as e:
                logger.error(f"切換失敗且無法回覆錯誤訊息: {e}", exc_info=True)
        return True  # 無論成功或失敗，都算處理過

    # 如果沒有匹配任何選單切換指令，則返回 False
    return False