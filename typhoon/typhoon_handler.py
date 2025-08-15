# typhoon/typhoon_handler.py
"""
處理用戶「颱風」查詢請求的總控制器（Handler）。
協調整個颱風資訊獲取的流程，從接收用戶請求到最終回覆 LINE 訊息。
執行流程：
1. 業務邏輯封裝 (TyphoonLogic)：
   - 將颱風查詢的複雜流程（呼叫 API、解析數據、格式化訊息）封裝在一個獨立的類別中。
   - 確保數據處理的順序性：先從 CWA API 取得原始資料，接著使用 `TyphoonParser` 解析，最後用 `typhoon_flex_message` 生成 LINE 訊息。
   - 處理流程中的任何錯誤（如 API 失敗、數據解析失敗），並返回 `None`。
2. 事件處理入口 (handle_typhoon_message)：
   - 作為 LINE 機器人 webhook 的一個入口點，由 `text_router.py` 呼叫。
   - 負責接收 LINE 的訊息事件，並協調 `TyphoonLogic` 類別來執行任務。
   - 根據 `TyphoonLogic` 返回的結果，決定回覆用戶一個精美的 Flex Message 或是簡單的文字錯誤訊息。
"""
import logging
from typing import Any, Dict, Optional

from linebot.v3.messaging import MessagingApi
from linebot.v3.messaging.models import TextMessage, FlexMessage
from linebot.v3.webhooks.models import MessageEvent

from config import CWA_API_KEY
from utils.line_common_messaging import send_line_reply_message

from .typhoon_parser import TyphoonParser
from .cwa_typhoon_api import TyphoonApiClient
from .typhoon_flex_message import create_typhoon_flex_message

logger = logging.getLogger(__name__)

# --- 處理颱風相關的業務邏輯，協調 API 呼叫、數據解析和訊息格式化 ---
class TyphoonLogic:
    # --- 初始化 `TyphoonLogic` 類別 ---
    def __init__(self):
        if not CWA_API_KEY: # 檢查 API 授權碼是否存在
            logger.critical("CWA_API_KEY 未設定。無法初始化颱風邏輯。")
            raise ValueError("CWA_API_KEY 未設定。")
        # 初始化 API 客戶端和解析器
        self.api_client = TyphoonApiClient(CWA_API_KEY)
        self.parser = TyphoonParser()

    # --- 獲取原始颱風數據並進行解析 ---
    def fetch_and_parse_typhoon_data(self) -> Optional[Dict[str, Any]]:
        # 1. 從中央氣象署 API 取得未經處理的原始颱風資料 (通過 self.api_client 調用)
        raw_data = self.api_client.fetch_typhoon_raw_data()
        if not raw_data:
            logger.warning("無法獲取颱風原始資料，無法生成 Flex Message。")
            return None
        
        # 2. 將複雜的原始 JSON 數據轉換成一個更簡潔、易於使用的字典 (通過 self.parser 調用)
        parsed_data = self.parser.parse_typhoon_data(raw_data)
        if not parsed_data:
            logger.warning("無法解析颱風數據，無法生成 Flex Message。")
            return None
        
        return parsed_data # 回傳解析後的字典
        
    # --- 獲取並處理颱風數據，返回包含解析數據和 Flex Message 的元組 ---
    def get_typhoon_info_and_message(self) -> Optional[tuple[dict, FlexMessage]]:
        """
        這是供外部呼叫的主要方法，封裝了數據獲取、解析和訊息生成的所有步驟。
        """
        # 1. 獲取解析後的數據
        parsed_data = self.fetch_and_parse_typhoon_data()
        if not parsed_data:
            return None # 如果數據獲取或解析失敗，直接返回 None，讓呼叫者（handle_typhoon_message）決定如何回覆用戶

        # 2. 生成 Flex Message
        try:
            """
            將處理好的數據轉換為 LINE 訊息物件。
            呼叫 `create_typhoon_flex_message` 函式，將解析後的數據傳入。
            使用 `try...except` 區塊，以防在生成 Flex Message 的過程中發生任何意外錯誤，例如數據結構與預期不符導致的 `KeyError`。
            為了提高穩定性，增加了 `isinstance` 檢查，確保 `create_typhoon_flex_message` 函式確實返回了 `FlexMessage` 類型的物件，避免將錯誤的物件傳給 LINE API。
            """
            flex_message_object = create_typhoon_flex_message(parsed_data)
            if not isinstance(flex_message_object, FlexMessage): # 確保 create_typhoon_flex_message 返回的是 FlexMessage 物件
                logger.error("create_typhoon_flex_message 未返回 FlexMessage 物件。")
                return None
            return parsed_data, flex_message_object # 回傳所有需要的資訊
        except Exception as e:
            logger.error(f"生成颱風 Flex Message 時發生錯誤: {e}", exc_info=True)
            return None
        
# --- 處理來自 LINE 的颱風查詢訊息事件 ---
def handle_typhoon_message(api: MessagingApi, event: MessageEvent) -> bool:
    """
    這是 text_router.py 會呼叫的入口函式。
    這個函式是整個颱風處理流程的起點，接收 LINE 的事件物件，並協調 `TyphoonLogic` 類別來完成後續的業務邏輯。
    不處理具體的數據解析和訊息生成，而是專注於「控制流程」和「發送回應」。
    """
    user_id = event.source.user_id
    reply_token = event.reply_token

    logger.info(f"[TyphoonHandler] 收到用戶 '{user_id}' 的颱風查詢請求。")

    # 初始化 `TyphoonLogic` 類別
    """
    使用 `try...except` 區塊來包裝初始化過程，以捕獲在 `TyphoonLogic.__init__` 中可能拋出的 `ValueError`。
    如果初始化失敗，說明系統配置有問題（如 API 金鑰缺失），程式會發送一個友善的錯誤訊息給用戶，並立即返回。
    """
    try:
        typhoon_logic = TyphoonLogic()
    except ValueError as e:
        logger.critical(f"[TyphoonHandler] 初始化 TyphoonLogic 失敗: {e}")
        send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，系統配置錯誤，無法提供颱風資訊。請聯繫管理員。")])
        return True

    # 執行業務邏輯並獲取 Flex Message
    result = typhoon_logic.get_typhoon_info_and_message()

    # 根據結果回覆訊息
    """
    根據 `get_typhoon_info_and_message` 的回傳結果，決定要回覆哪種訊息。
    - 成功 (`if result`)：如果成功獲得一個 Flex Message 物件，則呼叫 `send_line_reply_message` 來發送這個精美的卡片。
    - 失敗 (`else`)：如果 `get_typhoon_info_and_message` 返回 `None`，說明在 API 呼叫或數據解析環節發生了錯誤，此時程式會回覆一個簡單的文字訊息來告知用戶，確保用戶不會收到空的回應。
    - 異常處理：在發送 Flex Message 的過程中，也可能發生網路或 LINE API 相關的錯誤；因此，再次使用 `try...except` 區塊，如果發送失敗，則退回到發送一個文字訊息。
    - 返回布林值：函式最後都返回 `True`，表示這個事件已被成功處理，不需要再由其他函式處理。
    """
    if result:
        parsed_data, flex_message_object = result # 接收回傳的元組，但只使用 Flex Message
        try:
            send_line_reply_message(api, reply_token, [flex_message_object])
            logger.info(f"[TyphoonHandler] 成功回覆用戶 '{user_id}' 颱風 Flex Message。")
            return True # 表示事件已處理
        except Exception as e:
            logger.error(f"[TyphoonHandler] 回覆颱風 Flex Message 失敗: {e}", exc_info=True)
            send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，颱風資訊回覆時發生錯誤，請稍候再試。")])
            return True # 雖然失敗，但也算處理過
    else:
        send_line_reply_message(api, reply_token, [TextMessage(text="目前無法取得颱風資訊，請稍候再試。")])
        logger.warning(f"[TyphoonHandler] 無法為用戶 '{user_id}' 取得或生成颱風資訊。")
        return True # 表示事件已處理