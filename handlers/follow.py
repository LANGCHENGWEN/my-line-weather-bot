# handlers/follow.py
import json
import logging

from user_data_manager import set_user_state
from utils.api_helper import get_messaging_api # 用來拿 MessagingApi instance
from utils.rich_menu_helper import get_rich_menu_id
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
    set_user_state(user_id, "awaiting_default_city_input")

    # 綁定 Rich Menu（使用 Rich Menu ID）
    rich_menu_id = get_rich_menu_id(DEFAULT_ALIAS)
    logger.info("DEBUG 預設 RichMenu ID = %s", rich_menu_id)

    # 綁定預設 Rich Menu
    if rich_menu_id:
        try:
            line_bot_api.link_rich_menu_id_to_user(user_id, rich_menu_id)
        except Exception as e:
            logger.error(f"Link default rich-menu failed: {e}")
    else:
        logger.error("Rich Menu ID 無法讀取，無法綁定")
