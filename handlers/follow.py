# handlers/follow.py
"""
這個檔案主要負責處理使用者追蹤（follow）或解除封鎖（unblock）Line Bot 的事件。
它的核心職責是為新加入或重新啟用的使用者提供一個順暢的首次互動體驗，包括發送歡迎訊息、引導他們設定預設城市，以及為他們綁定預設的 Rich Menu (圖文選單)。
"""
import logging
from utils.api_helper import get_messaging_api
from utils.firestore_manager import set_user_state
from utils.line_common_messaging import send_hello_message
from rich_menu_manager.rich_menu_helper import get_rich_menu_id

logger = logging.getLogger(__name__)

DEFAULT_ALIAS = "main_menu_alias"

def handle(event):
    """
    這是追蹤事件的處理函式。
    當使用者追蹤或解除封鎖機器人時，這個函式會被觸發。
    負責執行一系列的初始化設定，包括傳送歡迎訊息、設定使用者狀態、以及綁定 Rich Menu。
    """
    user_id = event.source.user_id
    reply_token = event.reply_token
    line_bot_api = get_messaging_api()

    # --- 發送 Flex 歡迎訊息 ---
    send_hello_message(line_bot_api, user_id, reply_token)

    # --- 設定用戶狀態 → 等待輸入預設城市 ---
    # 這個函式負責開始流程，city_input_handler.py 負責接收並完成流程
    """
    為了引導使用者設定預設城市，這裡將用戶狀態設定為 "awaiting_default_city_input"。
    程式這樣寫是因為這是一種「狀態機」的設計模式。
    當使用者處於這個狀態時，任何文字輸入都會被 `city_input_handler.py` 中的 `handle_awaiting_default_city_input` 函式所處理，直到使用者成功輸入一個有效的縣市名稱為止。
    """
    set_user_state(user_id, "awaiting_default_city_input") # 使用者輸入一個預設城市

    # --- 綁定 Rich Menu（使用 Rich Menu ID）---
    # 1. 取得預設 Rich Menu 的 ID，這個 ID 是用來讓機器人知道要綁定哪個圖文選單
    rich_menu_id = get_rich_menu_id(DEFAULT_ALIAS)
    logger.info("預設 RichMenu ID = %s", rich_menu_id)

    # 2. 用 Rich Menu ID 綁定預設 Rich Menu
    """
    在使用者追蹤機器人時，自動為他們綁定一個預設的 Rich Menu。
    在使用者還沒有設定預設城市前，他們無法使用某些功能，因此綁定一個 Rich Menu，可以讓他們更容易找到和使用機器人的基本功能。
    這裡使用 `try...except` 區塊來處理可能發生的錯誤，確保即使綁定失敗，也不會導致程式崩潰。
    """
    if rich_menu_id:
        try:
            line_bot_api.link_rich_menu_id_to_user(user_id, rich_menu_id)
        except Exception as e:
            logger.error(f"連結預設 Rich Menu 失敗: {e}")
    else:
        logger.error("Rich Menu ID 無法讀取，無法綁定。")