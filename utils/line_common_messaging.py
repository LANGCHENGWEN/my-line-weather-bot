# line_common_messaging.py
# 通用訊息
import json
import logging
from typing import List, Union
from linebot.v3.messaging import MessagingApi
from linebot.v3.messaging.models import Message, TextMessage, ReplyMessageRequest, PushMessageRequest
from linebot.v3.webhooks.models import MessageEvent
from linebot.v3.exceptions import InvalidSignatureError

from utils.flex_templates import build_hello_flex
from utils.message_builder import format_text_message
# from linebot.models.flex_message import BubbleContainer
# FlexContainer

logger = logging.getLogger(__name__)

# --- 訊息發送函數 ---
def send_line_push_message(line_bot_api_instance, user_id: str, messages: List[Message]):
    """
    通用發送 LINE 推播訊息函數 (機器人主動發送)。
    需要接收一個 Line Bot SDK 的 Message 物件。
    不需要 reply_token。
    """
    try:
        if not messages: # <-- ADDED: Check if messages list is empty
            logger.warning("沒有訊息可推播。")
            return

        # 構建 PushMessageRequest 物件
        push_message_request = PushMessageRequest(
            to=user_id,
            messages=messages # messages 參數需要一個訊息物件的列表
        )

        # 使用 Line API 實例發送訊息
        line_bot_api_instance.push_message(push_message_request)

        logger.info(f"訊息已成功推播給用戶 ID: {user_id}")
    except Exception as e:
        logger.error(f"推播訊息給 {user_id} 時發生錯誤: {e}", exc_info=True)

        '''
        messages = []
        if isinstance(message_text, str):
            messages.append(TextMessage(text=message_text))
            logger.info("準備推播 TextMessage。")
        elif isinstance(message_text, FlexMessage): # 處理 FlexMessage
            messages.append(message_text)
            logger.info("準備推播 FlexMessage。")
        else:
            logger.error(f"不支持的推播訊息內容類型: {type(message_text)}")
            return # 不支持的類型直接返回
        '''

def send_line_reply_message(line_bot_api_instance: MessagingApi, reply_token: str, messages: Union[Message, List[Message]], user_id: str = None):
    """
    通用發送 LINE 回覆訊息函數 (針對用戶訊息進行回覆)。
    需要接收一個 Line Bot SDK 的 Message 物件。
    需要 reply_token。
    messages 可以是單個 Message，也可以是 List[Message]。
    """
    if not isinstance(messages, list):
        messages = [messages]

    reply_message_request = ReplyMessageRequest(
        reply_token=reply_token,
        messages=messages
    )
    
    # --- 新增的偵錯日誌 ---
    logger.debug(f"DEBUG: 準備發送回覆。Reply Token: {reply_token}")
    try:
        # 將訊息物件轉換為字典列表以便輸出，方便檢查內容
        messages_as_dict = [m.to_dict() for m in messages]
        logger.debug(f"DEBUG: 準備發送的訊息內容: {json.dumps(messages_as_dict, indent=2, ensure_ascii=False)}")
    except Exception as e:
        logger.error(f"DEBUG: 無法序列化訊息物件用於日誌: {e}")
    # --- 偵錯日誌結束 ---

    try:
        line_bot_api_instance.reply_message(reply_message_request)
        logger.info(f"成功回覆訊息 (reply_token: {reply_token})")
    except InvalidSignatureError as e:
        logger.error(f"回覆訊息失敗 (API 錯誤 - reply_token: {reply_token}): ({e.status})\nReason: {e.reason}\nHTTP response body: {e.body}", exc_info=True)
        # 如果是 Invalid reply token 錯誤，嘗試發送 push 訊息作為備用
        if "Invalid reply token" in e.body and user_id:
            logger.warning(f"Reply token 無效，嘗試將訊息作為 Push 訊息發送給用戶 {user_id}。")
            try:
                push_request = PushMessageRequest(
                    to=user_id,
                    messages=messages
                )
                line_bot_api_instance.push_message(push_request)
                logger.info(f"成功將訊息作為 Push 訊息發送給用戶 {user_id} (原 reply_token: {reply_token})。")
            except InvalidSignatureError as push_e:
                logger.error(f"Push 訊息發送失敗 (API 錯誤 - 用戶 {user_id}): ({push_e.status})\nReason: {push_e.reason}\nHTTP response body: {push_e.body}", exc_info=True)
            except Exception as push_e:
                logger.error(f"Push 訊息發送時發生未知錯誤 (用戶 {user_id}): {push_e}", exc_info=True)
        else:
            logger.error(f"回覆訊息失敗 (非 reply token 錯誤 或 無法推播) - reply_token: {reply_token}", exc_info=True)
    except Exception as e:
        logger.error(f"回覆訊息失敗 (未知錯誤 - reply_token: {reply_token}): {e}", exc_info=True)

        '''
        messages = []
        if isinstance(message_text, str):
            messages.append(TextMessage(text=message_text))
            logger.info("準備回覆 TextMessage。")
        elif isinstance(message_text, FlexMessage): # 處理 FlexMessage
            messages.append(message_text)
            logger.info("準備回覆 FlexMessage。")
        else:
            logger.error(f"不支持的回覆訊息內容類型: {type(message_text)}")
            return # 不支持的類型直接返回
        '''

# --- 特定情境的訊息發送函數 (會呼叫上面的通用發送函數和格式化函數) ---
def send_hello_message(line_bot_api_instance, user_id: str, reply_token: str):
    """
    發送歡迎 Flex 卡片。
    若 Flex 失敗（極少見），回退純文字。
    """
    try:
        flex_msg = build_hello_flex()
        send_line_reply_message(line_bot_api_instance, reply_token, flex_msg)
        logger.info(f"已發送 Flex 歡迎語給用戶 ID: {user_id}")
    except Exception as e:
        logger.error(f"發送 Flex 歡迎訊息失敗，改用純文字：{e}", exc_info=True)
        fallback_text = (
            "哈囉！您好～我是暖心天氣語。\n"
            "請先輸入您想預設的城市名稱，例如「台中市」或「台北市」，讓我幫您設定預設城市！"
        )
        send_line_reply_message(
            line_bot_api_instance,
            reply_token,
            format_text_message(fallback_text)
        )

def send_unrecognized_message(line_bot_api_instance: MessagingApi, event: MessageEvent):
    """
    發送一個表示訊息未被識別的通用回覆訊息。
    接收 Line event 物件以獲取 reply_token 和 user_id。
    """
    user_id = event.source.user_id
    reply_token = event.reply_token

    logger.info(f"已發送不明白訊息給用戶 ID: {user_id}")
    try:
        line_bot_api_instance.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text="抱歉，我不明白您的意思。請嘗試使用菜單或其他指令。")]
            )
        )
        logger.info(f"成功發送不明白訊息給用戶 ID: {user_id}")
        return True # 表示成功發送
    except Exception as e:
        logger.error(f"回覆未識別訊息失敗 (user_id={user_id}): {e}", exc_info=True)
        # 如果需要，可以記錄 HTTP response headers/body
        # logger.error(f"HTTP response headers: {e.http_resp.headers}")
        # logger.error(f"HTTP response body: {e.http_resp.data}")
        return False # 表示發送失敗

def send_api_error_message(line_bot_api_instance, user_id: str, reply_token: str, location_name: str = ""):
    """發送 API 錯誤訊息，用於回覆用戶。"""
    text = f"抱歉，目前無法取得{' ' + location_name if location_name else ''}的天氣資訊，請稍候再試。"
    message_to_send = format_text_message(text)
    send_line_reply_message(line_bot_api_instance, reply_token, [message_to_send])
    logger.warning(f"已發送 API 錯誤訊息給用戶 ID: {user_id}")

def send_test_notification_setup_message(user_id: str):
    """返回用於開發者介面測試的提示訊息 (此函數不發送訊息，僅返回字串)"""
    return "請在 config.py 中設定 YOUR_LINE_USER_ID 來測試每日通知。"


"""
# --- 測試程式碼 ---
if __name__ == "__main__":
    # 設置日誌級別以便在測試時看到詳細輸出
    logging.getLogger().setLevel(logging.DEBUG) 
    
    logger.debug("\n--- 開始測試 line_messaging.py ---")

    # 創建一個 Mock 物件來模擬 line_bot_api_instance
    # 這個 Mock 物件會有一個 `push_message` 方法，我們可以檢查它是否被呼叫
    mock_line_api = Mock()
    test_user_id = "U1234567890abcdef" # 測試用的用戶 ID

    # --- 測試 format_weather_message ---
    logger.debug("\n--- 測試 format_weather_message ---")
    mock_weather_data = {
        'min_temp': 20,
        'max_temp': 28,
        'pop': 30,
        'weather_desc': '多雲時晴',
        'wind_speed': 2.5,
        'comfort_index': '舒適'
    }
    test_area = "臺北市"
    formatted_message = format_weather_message(mock_weather_data, test_area)
    logger.debug(f"格式化後的天氣訊息:\n{formatted_message}")
    # 你可以在這裡添加斷言，例如檢查訊息開頭或包含關鍵詞
    assert "📍 **臺北市 今日天氣**" in formatted_message
    assert "🌡️ 氣溫: 20°C ~ 28°C" in formatted_message
    assert "☔ 降雨機率: 30%" in formatted_message
    logger.debug("format_weather_message 測試通過！")

    # 測試沒有天氣數據的情況
    formatted_no_data_message = format_weather_message({}, "未知地點")
    logger.debug(f"格式化沒有數據的天氣訊息:\n{formatted_no_data_message}")
    assert "抱歉，無法取得 未知地點 的天氣資訊。" in formatted_no_data_message
    logger.debug("format_weather_message (無數據) 測試通過！")


    # --- 測試 send_line_message ---
    logger.debug("\n--- 測試 send_line_message ---")
    test_message = "這是一條測試訊息！"
    send_line_message(mock_line_api, test_user_id, test_message)
    # 檢查 mock_line_api 的 push_message 方法是否被呼叫，以及傳入的參數是否正確
    # mock_line_api.push_message.assert_called_once_with(test_user_id, TextMessage(text=test_message))
    
    # 為了兼容 TextMessage 實例的比較，可能需要更精確的檢查
    # 更好的檢查方法是檢查 call_args，並比較 TextMessage 的 text 屬性
    mock_line_api.push_message.assert_called_once() # 確保被呼叫一次
    
    # 獲取被呼叫時的參數
    args, kwargs = mock_line_api.push_message.call_args
    # 檢查第一個參數是否是用戶 ID
    assert args[0] == test_user_id
    # 檢查第二個參數是否是 TextMessage 實例，並且內容正確
    assert isinstance(args[1], TextMessage)
    assert args[1].text == test_message
    logger.debug("send_line_message 測試通過！")

    # 重置 mock 狀態以便進行下一個測試
    mock_line_api.reset_mock()


    # --- 測試 send_hello_message ---
    logger.debug("\n--- 測試 send_hello_message ---")
    send_hello_message(mock_line_api, test_user_id)
    mock_line_api.push_message.assert_called_once()
    args, kwargs = mock_line_api.push_message.call_args
    assert args[0] == test_user_id
    assert isinstance(args[1], TextMessage)
    assert "哈囉！您好~ 我是暖心天氣語" in args[1].text
    logger.debug("send_hello_message 測試通過！")
    mock_line_api.reset_mock()


    # --- 測試 send_unrecognized_message ---
    logger.debug("\n--- 測試 send_unrecognized_message ---")
    send_unrecognized_message(mock_line_api, test_user_id)
    mock_line_api.push_message.assert_called_once()
    args, kwargs = mock_line_api.push_message.call_args
    assert args[0] == test_user_id
    assert isinstance(args[1], TextMessage)
    assert "抱歉，我不明白您的意思" in args[1].text
    logger.debug("send_unrecognized_message 測試通過！")
    mock_line_api.reset_mock()


    # --- 測試 send_api_error_message ---
    logger.debug("\n--- 測試 send_api_error_message ---")
    send_api_error_message(mock_line_api, test_user_id, "高雄市")
    mock_line_api.push_message.assert_called_once()
    args, kwargs = mock_line_api.push_message.call_args
    assert args[0] == test_user_id
    assert isinstance(args[1], TextMessage)
    logger.debug(f"DEBUG: 實際收到的 API 錯誤訊息: '{args[1].text}'")
    assert "抱歉，目前無法取得 高雄市 的天氣資訊" in args[1].text
    logger.debug("send_api_error_message 測試通過！")
    mock_line_api.reset_mock()

    send_api_error_message(mock_line_api, test_user_id) # 測試沒有 area_name
    mock_line_api.push_message.assert_called_once()
    args, kwargs = mock_line_api.push_message.call_args
    assert args[0] == test_user_id
    assert isinstance(args[1], TextMessage)
    logger.debug(f"DEBUG: 實際收到的 API 錯誤訊息 (無區域名稱): '{args[1].text}'")
    assert "抱歉，目前無法取得的天氣資訊" in args[1].text # 注意這裡沒有 area_name
    logger.debug("send_api_error_message (無區域名稱) 測試通過！")
    mock_line_api.reset_mock()


    # --- 測試 send_test_notification_setup_message ---
    logger.debug("\n--- 測試 send_test_notification_setup_message ---")
    test_setup_msg = send_test_notification_setup_message(test_user_id)
    logger.debug(f"測試設定訊息: {test_setup_msg}")
    assert "請在 config.py 中設定 YOUR_LINE_USER_ID 來測試每日通知。" in test_setup_msg
    # 這個函數不應該呼叫 push_message，因為它只返回字串
    mock_line_api.push_message.assert_not_called() 
    logger.debug("send_test_notification_setup_message 測試通過！")


    logger.debug("\n--- 所有 line_messaging.py 測試完成！ ---")
"""