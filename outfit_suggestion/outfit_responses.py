# outfit_suggestion/outfit_responses.py
import logging
from linebot.v3.messaging import ApiClient
from linebot.v3.messaging.models import TextMessage, FlexMessage

# 從您現有的檔案引入 Flex Message 建立器
from outfit_suggestion.outfit_type_flex_messages import build_outfit_suggestions_flex

from utils.text_processing import normalize_city_name
from utils.line_common_messaging import send_line_reply_message # 假設您有這個實用工具

# 載入使用者狀態管理器
from utils.user_data_manager import set_user_state, get_default_city

logger = logging.getLogger(__name__)

def reply_outfit_weather_of_city(api: ApiClient, reply_token: str, user_id: str, city_name: str) -> bool:
    """
    接收用戶輸入的城市，並回覆該城市的穿搭建議主選單 (Flex Message)。

    Args:
        api (ApiClient): LINE Bot API 物件。
        reply_token (str): 接收到的訊息 reply_token。
        user_id (str): 觸發此操作的用戶 ID。
        city_name (str): 用戶輸入並驗證後的城市名稱。
    Returns:
        bool: 如果成功發送訊息則返回 True，否則返回 False。
    """
    try:
        logger.info(f"[OutfitResponses] 用戶 {user_id} 請求指定縣市 {city_name} 的穿搭建議選單。")

        city_normalized = normalize_city_name(city_name)

        default_user_city = get_default_city(user_id)

        if default_user_city is not None:
            default_user_city_normalized = normalize_city_name(default_user_city)
        else:
            # 如果沒有預設城市，則使用這個預設顯示文字
            default_user_city_normalized = "未設定" # 或者你希望的預設顯示文字

        # 🚀 新增這一行日誌來檢查 default_user_city_normalized 的值
        logger.debug(f"[OutfitResponses] 用戶 {user_id} 的預設城市 (from DB): {default_user_city_normalized}")

        # 再次發送穿搭建議選單，但以用戶輸入的城市為主
        flex_message = build_outfit_suggestions_flex(
            target_query_city=city_normalized,
            default_city_display=default_user_city_normalized
        )

        if flex_message:
            send_line_reply_message(api, reply_token, [flex_message])
            logger.info(f"[OutfitResponses] 成功回覆穿搭建議選單（針對指定城市 {city_normalized}）給 {user_id}。")
            # 清空等待輸入城市的狀態，並設定為等待天數選擇
            set_user_state(user_id, "awaiting_outfit_selection", data={"city": city_normalized}) 
            return True
        else:
            logger.error(f"[OutfitResponses] build_outfit_suggestions_flex 返回 None 或空。Flex Message 可能有問題。")
            send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，無法載入該城市的穿搭建議選單，請稍候再試。")])
            return False # Flex Message 建立失敗，返回 False
    except Exception as e:
        logger.error(f"[OutfitResponses] 處理穿搭建議回覆時發生錯誤，用戶 {user_id}, 城市 {city_name}: {e}", exc_info=True)
        send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，處理您的請求時發生錯誤，請稍後再試。")])
        return False

    try:
        # 首先發送一個確認訊息，讓用戶知道 Bot 已經接收到城市
        confirmation_message = TextMessage(text=f"好的，已為您設定查詢 {city_name} 的穿搭建議。")

        # 接著，構建您現有的穿搭建議 Flex Message
        outfit_flex_message = build_outfit_suggestions_flex()

        # 將確認訊息和 Flex Message 一起回覆給用戶
        # 注意：reply_message 接受一個訊息物件的列表
        send_line_reply_message(api, reply_token, [confirmation_message, outfit_flex_message])

        logger.info(f"成功回覆 {city_name} 的穿搭建議選單給用戶。")

    except Exception as e:
        logger.error(f"回覆 {city_name} 的穿搭建議選單時發生錯誤: {e}", exc_info=True)
        # 如果回覆失敗，發送一個簡單的文字錯誤訊息
        send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，生成穿搭建議選單時發生問題。")])