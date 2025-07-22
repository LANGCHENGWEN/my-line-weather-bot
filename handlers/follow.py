# handlers/follow.py
# 為新加入或重新啟用的使用者提供一個順暢且個人化的首次互動體驗，引導他們開始使用 Line Bot 的各種功能
import json
import logging

from rich_menu_manager.rich_menu_helper import get_rich_menu_id

from utils.user_data_manager import set_user_state
from utils.api_helper import get_messaging_api # 用來拿 MessagingApi instance
from utils.line_common_messaging import send_hello_message

logger = logging.getLogger(__name__)

DEFAULT_ALIAS = "main_menu_alias"

def handle(event):
    user_id = event.source.user_id
    reply_token = event.reply_token
    line_bot_api = get_messaging_api()

    # 1) 發送歡迎 Flex 或純文字
    send_hello_message(line_bot_api, user_id, reply_token)

    # 2) 設定用戶狀態 → 等待輸入預設城市
    # 這個檔案負責開始流程，default_city_input.py負責接收並完成流程
    set_user_state(user_id, "awaiting_default_city_input") # 使用者輸入一個預設城市

    # 綁定 Rich Menu（使用 Rich Menu ID）
    rich_menu_id = get_rich_menu_id(DEFAULT_ALIAS)
    logger.info("預設 RichMenu ID = %s", rich_menu_id)

    # 綁定預設 Rich Menu
    if rich_menu_id:
        try:
            line_bot_api.link_rich_menu_id_to_user(user_id, rich_menu_id)
        except Exception as e:
            logger.error(f"Link default rich-menu failed: {e}")
    else:
        logger.error("Rich Menu ID 無法讀取，無法綁定")
