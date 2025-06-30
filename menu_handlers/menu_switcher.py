# menu_handlers/menu_switcher.py

import logging
from linebot.v3.messaging import MessagingApi
from linebot.v3.webhooks.models import MessageEvent
from linebot.v3.exceptions import InvalidSignatureError
from config import setup_logging

from utils.rich_menu_helper import get_rich_menu_id

# 從 rich_menu_configs.py 匯入 Rich Menu 別名常數
from rich_menu_manager.rich_menu_configs import ( # 確保路徑正確
    MAIN_MENU_ALIAS,
    WEATHER_QUERY_ALIAS,
    TYPHOON_ZONE_ALIAS,
    LIFE_REMINDER_ALIAS,
    SETTINGS_ALIAS
)
from .menu_reply import build_text_reply

logger = setup_logging(__name__)

# ---------- 可注入的別名表 ---------- #
_alias_map = {
    "main":      MAIN_MENU_ALIAS,
    "weather":   WEATHER_QUERY_ALIAS,
    "typhoon":   TYPHOON_ZONE_ALIAS,
    "life":      LIFE_REMINDER_ALIAS,
    "settings":  SETTINGS_ALIAS,
}

def init_menu_aliases(main_alias, weather_alias, typhoon_alias,
                      life_alias, settings_alias):
    """
    啟動時呼叫一次，將實際 Rich‑Menu alias/ID
    注入本模組，供 handle_menu_switching() 使用。
    """
    global _alias_map
    _alias_map = {
        "main":      main_alias,
        "weather":   weather_alias,
        "typhoon":   typhoon_alias,
        "life":      life_alias,
        "settings":  settings_alias,
    }
    logger.info(f"menu_switcher: _alias_map 已初始化 → {_alias_map}")

def _link_rich_menu_by_alias(line_bot_api: MessagingApi, user_id: str, alias_id: str) -> bool:
    """
    輔助函式：透過 Rich Menu 別名獲取 ID 並綁定給用戶。
    輔助函式：先用 JSON (get_rich_menu_id) 取 ID；若取不到再呼叫 LINE API。
    """
    try:
        # 1. 透過別名獲取 Rich Menu 詳細資訊
        rich_menu_alias_info = line_bot_api.get_rich_menu_alias(alias_id)
        # 從資訊中提取實際的 Rich Menu ID
        rich_menu_id = rich_menu_alias_info.rich_menu_id

        # 1. 先嘗試從本地 JSON 取得 ID
        rich_menu_id = get_rich_menu_id(alias_id)

        # 2. 若 JSON 取不到，再呼叫 LINE API 要 ID（避免第一次啟動沒有 JSON）
        if not rich_menu_id:
            alias_info = line_bot_api.get_rich_menu_alias(alias_id)
            rich_menu_id = alias_info.rich_menu_id

        # 2. 使用獲取到的 Rich Menu ID 綁定給用戶
        line_bot_api.link_rich_menu_id_to_user(user_id, rich_menu_id)
        logger.info(f"成功將 Rich Menu ID '{rich_menu_id}' (來自別名 '{alias_id}') 綁定給用戶 '{user_id}'。")
        return True
    except InvalidSignatureError as e:
        logger.error(f"LINE API 錯誤：無法綁定 '{alias_id}' -> {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"未知錯誤：綁定 '{alias_id}' 失敗 -> {e}", exc_info=True)
        return False

def handle_menu_switching(event: MessageEvent, line_bot_api: MessagingApi) -> bool:
    """
    根據用戶發送的訊息文本，嘗試切換用戶的 Rich Menu。
    :param event: LINE Webhook 事件對象
    :param line_bot_api: MessagingApi 客戶端實例
    :return: 如果成功處理了 Rich Menu 切換，則返回 True；否則返回 False。
    """
    if not hasattr(event, 'message') or not hasattr(event.message, 'text'):
        # 如果不是文本訊息，不處理選單切換
        return False

    text = event.message.text
    user_id = event.source.user_id
    reply_token = event.reply_token

    menu_switch_map = {
        "天氣查詢": _alias_map.get("weather"),
        "颱風專區": _alias_map.get("typhoon"),
        "生活提醒": _alias_map.get("life"),
        "設定": _alias_map.get("settings"),
        "回上一頁": _alias_map.get("main")  # 假設「回上一頁」就是回到主選單
    }

    if text in menu_switch_map:
        target_alias = menu_switch_map[text]
        logger.info(f"嘗試切換到 '{text}' 選單 (別名: {target_alias})，用戶: {user_id}")

        if _link_rich_menu_by_alias(line_bot_api, user_id, target_alias):
            # 可選：回覆用戶確認切換
            reply_text = "已返回主選單。" if text == "回上一頁" else f"已切換至 {text} 選單。"
            try:
                reply_req = build_text_reply(reply_text, reply_token)
                line_bot_api.reply_message(reply_req)
                logger.info(f"成功回覆用戶 '{user_id}' 訊息：{reply_text}")
                return True
            except Exception as e:
                logger.error(f"回覆用戶訊息失敗: {e}", exc_info=True)
                # 如果回覆失敗，這裡不應該再嘗試回覆，避免無限循環或再次報錯
        else:
            # 切換選單失敗時的回覆
            try:
                error_req = build_text_reply("切換選單失敗，請稍後再試。", reply_token)
                line_bot_api.reply_message(error_req)
                logger.info(f"成功回覆用戶 '{user_id}' 錯誤訊息：{error_req}")
            except Exception as e:
                logger.error(f"切換失敗且無法回覆錯誤訊息: {e}", exc_info=True)
        return True  # 無論成功或失敗，都算處理過

    # 如果沒有匹配任何選單切換指令，則返回 False
    return False

'''
    # 確保別名已初始化
    if not _MAIN_MENU_ALIAS:
        logger.error("Rich Menu 別名未初始化！請先呼叫 init_menu_aliases。")
        return False

    if text == "天氣查詢":
        logger.info(f"切換到天氣查詢選單，用戶: {user_id}")
        try:
            line_bot_api.link_rich_menu_alias_to_user(
                rich_menu_alias_id=_WEATHER_QUERY_ALIAS, # 別名 ID
                user_id=user_id                          # 用戶 ID
            )
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="已切換至天氣查詢子選單。")]
                )
            )
            return True
        except Exception as e:
            logger.error(f"無法切換 Rich Menu 別名 '{_WEATHER_QUERY_ALIAS}' 給用戶 {user_id}: {e}", exc_info=True)
            return False
    elif text == "颱風專區":
        logger.info(f"切換到颱風專區選單，用戶: {user_id}")
        try:
            line_bot_api.link_rich_menu_alias_to_user(
                rich_menu_alias_id=_TYPHOON_ZONE_ALIAS, # 別名 ID
                user_id=user_id                          # 用戶 ID
            )
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="已切換至颱風專區子選單。")]
                )
            )
            return True
        except Exception as e:
            logger.error(f"無法切換 Rich Menu 別名 '{_TYPHOON_ZONE_ALIAS}' 給用戶 {user_id}: {e}", exc_info=True)
            return False
    elif text == "生活提醒":
        logger.info(f"切換到生活提醒選單，用戶: {user_id}")
        try:
            line_bot_api.link_rich_menu_alias_to_user(
                rich_menu_alias_id=_LIFE_REMINDER_ALIAS, # 別名 ID
                user_id=user_id                          # 用戶 ID
            )
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="已切換至生活提醒子選單。")]
                )
            )
            return True
        except Exception as e:
            logger.error(f"無法切換 Rich Menu 別名 '{_LIFE_REMINDER_ALIAS}' 給用戶 {user_id}: {e}", exc_info=True)
            return False
    elif text == "設定":
        logger.info(f"切換到設定選單，用戶: {user_id}")
        try:
            line_bot_api.link_rich_menu_alias_to_user(
                rich_menu_alias_id=_SETTINGS_ALIAS, # 別名 ID
                user_id=user_id                          # 用戶 ID
            )
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="已切換至設定子選單。")]
                )
            )
            return True
        except Exception as e:
            logger.error(f"無法切換 Rich Menu 別名 '{_SETTINGS_ALIAS}' 給用戶 {user_id}: {e}", exc_info=True)
            return False
    elif text == "回上一頁":
        logger.info(f"切換到回上一頁選單，用戶: {user_id}")
        try:
            line_bot_api.link_rich_menu_alias_to_user(
                rich_menu_alias_id=_MAIN_MENU_ALIAS, # 別名 ID
                user_id=user_id                          # 用戶 ID
            )
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="已回主選單。")]
                )
            )
            return True
        except Exception as e:
            logger.error(f"無法切換 Rich Menu 別名 '{_MAIN_MENU_ALIAS}' 給用戶 {user_id}: {e}", exc_info=True)
            return False
    return False # 如果不是選單切換指令，返回 False
'''