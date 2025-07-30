# typhoon/typhoon_handler.py
# 主要處理颱風用戶輸入的回覆邏輯
import os
import logging
from typing import Any, Dict, Optional

from linebot.v3.messaging import MessagingApi
from linebot.v3.messaging.models import TextMessage, FlexMessage, FlexBubble, ReplyMessageRequest
from linebot.v3.webhooks.models import MessageEvent

from config import CWA_API_KEY

from utils.api_helper import get_messaging_api
from utils.line_common_messaging import send_line_reply_message

from .typhoon_parser import TyphoonParser
from .cwa_typhoon_api import TyphoonApiClient
from .typhoon_flex_message import create_typhoon_flex_message # 假設 typhoon_flex_message.py 在上一層或同層

logger = logging.getLogger(__name__)

# 確保 create_typhoon_flex_message 能接受解析後的數據
# 如果 create_typhoon_flex_message 尚未修改以接受結構化數據，你需要先修改它
# def create_typhoon_flex_message(typhoon_data: Dict[str, Any]) -> FlexSendMessage:
#     # ... 使用 typhoon_data["currentStatus"] 和 typhoon_data["forecasts"] 來構建訊息 ...

class TyphoonLogic:
    """
    處理颱風相關的業務邏輯，協調 API 呼叫、數據解析和訊息格式化。
    """
    def __init__(self):
        if not CWA_API_KEY:
            logger.critical("CWA_API_KEY 未設定。無法初始化颱風邏輯。")
            raise ValueError("CWA_API_KEY 未設定。")
        self.api_client = TyphoonApiClient(CWA_API_KEY)
        self.parser = TyphoonParser()

    def get_typhoon_flex_message(self) -> Optional[FlexMessage]:
        """
        獲取並處理颱風數據，返回一個 Flex Message 物件。
        """
        # 1. 呼叫 API 獲取原始數據
        raw_data = self.api_client.fetch_typhoon_raw_data()
        if not raw_data:
            logger.warning("無法獲取颱風原始資料，無法生成 Flex Message。")
            return None

        # 2. 解析原始數據
        parsed_data = self.parser.parse_typhoon_data(raw_data)
        if not parsed_data:
            logger.warning("無法解析颱風數據，無法生成 Flex Message。")
            return None

        # 3. 生成 Flex Message
        # 注意：這裡需要將解析後的數據傳遞給 create_typhoon_flex_message
        # 你的 create_typhoon_flex_message 函式需要調整以接收這個結構化的 parsed_data
        try:
            if parsed_data:
                flex_message_object = create_typhoon_flex_message(parsed_data)
            else:
                # 如果解析失敗，返回一個預設的錯誤訊息 FlexMessage
                # create_typhoon_flex_message 已經處理了 parsed_typhoon_data 為 None 的情況
                flex_message_object = create_typhoon_flex_message(None)

            # 確保 create_typhoon_flex_message 返回的是 FlexMessage 物件
            if not isinstance(flex_message_object, FlexMessage):
                logger.error("create_typhoon_flex_message 未返回 FlexMessage 物件。")
                return None
            
            # 直接返回由 create_typhoon_flex_message 產生的 FlexMessage 物件
            return flex_message_object

        except Exception as e:
            logger.error(f"生成颱風 Flex Message 時發生錯誤: {e}", exc_info=True)
            return None
        
# --- 新增: LINE 事件處理入口函式 ---
def handle_typhoon_message(api: MessagingApi, event: MessageEvent) -> bool:
    """
    處理來自 LINE 的颱風查詢訊息事件。
    這是 text_router.py 會呼叫的入口函式。
    """
    user_id = event.source.user_id
    reply_token = event.reply_token

    logger.info(f"[TyphoonHandler] 收到用戶 '{user_id}' 的颱風查詢請求。")

    try:
        typhoon_logic = TyphoonLogic() # 在這裡初始化 TyphoonLogic
    except ValueError as e:
        logger.critical(f"[TyphoonHandler] 初始化 TyphoonLogic 失敗: {e}")
        send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，系統配置錯誤，無法提供颱風資訊。請聯繫管理員。")])
        return True

    flex_message_object = typhoon_logic.get_typhoon_flex_message()

    if flex_message_object:
        # 如果成功獲取到 Flex Message 物件，則回覆它
        try:
            send_line_reply_message(api, reply_token, [flex_message_object])
            logger.info(f"[TyphoonHandler] 成功回覆用戶 '{user_id}' 颱風 Flex Message。")
            return True # 表示事件已處理
        except Exception as e:
            logger.error(f"[TyphoonHandler] 回覆颱風 Flex Message 失敗: {e}", exc_info=True)
            # 如果 Flex Message 發送失敗，可以考慮發送一個 TextMessage 作為備用
            send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，颱風資訊回覆時發生錯誤，請稍候再試。")])
            return True # 雖然失敗，但也算處理過
    else:
        # 如果無法生成 Flex Message (例如 API 失敗或數據解析失敗)
        send_line_reply_message(api, reply_token, [TextMessage(text="目前無法取得颱風資訊，請稍候再試。")])
        logger.warning(f"[TyphoonHandler] 無法為用戶 '{user_id}' 取得或生成颱風資訊。")
        return True # 表示事件已處理

"""
# 範例使用 (取消註解可進行測試)
if __name__ == "__main__":
    # 在這裡模擬 main app 的行為，初始化並調用 TyphoonLogic
    # 確保 CWA_API_AUTHORIZATION_CODE 環境變數已設定
    # 並且 typhoon_flex_message.py 能夠被正確導入
    # 由於這裡需要實際的 FlexSendMessage 物件，如果沒有 LINE Bot SDK 環境，
    # 範例將只顯示解析後的數據。
    
    # 引入 create_typhoon_flex_message (請確認路徑正確)
    # 假設 typhoon_flex_message.py 在專案根目錄，此處可能需要調整導入路徑
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from typhoon_flex_message import create_typhoon_flex_message

    # 模擬 create_typhoon_flex_message 函式 (如果還沒將其修改為接受結構化數據)
    # def create_typhoon_flex_message(current_status: Dict[str, Any], forecast_24hr: Optional[Dict[str, Any]], forecast_48hr: Optional[Dict[str, Any]], forecast_72hr: Optional[Dict[str, Any]]) -> Any:
    #     print("\n--- 模擬呼叫 create_typhoon_flex_message ---")
    #     print("現況:", current_status)
    #     print("24小時預報:", forecast_24hr)
    #     print("48小時預報:", forecast_48hr)
    #     print("72小時預報:", forecast_72hr)
    #     return type('obj', (object,), {'contents': type('obj', (object,), {'as_json_dict': lambda self: {'type': 'bubble', 'body': {'type': 'box', 'layout': 'vertical', 'contents': []}}})()})() # 簡化模擬返回物件

    try:
        typhoon_logic = TyphoonLogic()
        flex_msg_json = typhoon_logic.get_typhoon_flex_message()

        if flex_msg_json:
            import json
            print("\n--- 生成的 Flex Message JSON ---")
            print(json.dumps(flex_msg_json, ensure_ascii=False, indent=2))
        else:
            print("無法生成颱風 Flex Message。")
    except ValueError as ve:
        print(f"設定錯誤: {ve}")
    except Exception as e:
        print(f"測試執行錯誤: {e}")
"""