# outfit_suggestion/outfit_type_flex_messages.py
from linebot.v3.messaging.models import (
    FlexBox, FlexText, FlexImage, FlexBubble,
    FlexButton, FlexMessage, FlexSeparator, PostbackAction
)

def build_outfit_suggestions_flex(target_query_city: str, default_city_display: str) -> FlexMessage:
    """
    生成一個單一 Flex Message 卡片選單，包含今日、即時、未來穿搭建議選項。
    只顯示用戶的預設城市。

    Args:
        target_query_city (str): 用戶當前查詢的城市名稱 (用於 Postback data)。
        default_city_display (str): 用戶預設城市（用於顯示，如果沒有則為「未設定」）。
    Returns:
        FlexMessage: 可以直接用來構建 FlexMessage 的 LINE Bot SDK 物件。
    """
    # 輔助函式，用於生成穿搭建議按鈕
    def _outfit_button(label: str, data_type: str) -> FlexButton:
        return FlexButton(
            action=PostbackAction(
                label=label,
                data=f"action=outfit_query&type={data_type}&city={target_query_city}"
            ),
            style="primary",
            color="#00B900",  # LINE 綠色，使按鈕更顯眼
            height="sm",
            margin="md"
        )

    # 查詢其他縣市按鈕
    def _other_location_button() -> FlexButton:
        return FlexButton(
            action=PostbackAction(
                type="postback",
                label="查詢其他縣市",
                data="action=outfit_other_city" # 新增一個用於查詢其他縣市的 action
            ),
            style="secondary",
            color="#AAAAAA", # 灰色，與主要按鈕區隔
            height="sm",
            margin="lg" # 增加上方間距，與穿搭建議按鈕區隔
        )
    
    bubble = FlexBubble(
        direction="ltr",
        hero=FlexBox(
            layout="vertical",
            contents=[
                FlexImage(
                    url="https://i.imgur.com/your_outfit_menu_banner.png", # 請替換成你菜單的橫幅圖片 URL
                    size="full",
                    aspectRatio="20:9",
                    aspectMode="cover"
                )
            ]
        ),
        body=FlexBox(
            layout="vertical",
            contents=[
                FlexText(
                    text="👗 穿搭建議 👔",
                    weight="bold",
                    size="xl",
                    align="center",
                    margin="md"
                ),
                FlexText(
                    text=f"您的預設城市：{default_city_display}", # 顯示用戶預設城市
                    size="sm",
                    color="#666666",
                    align="center",
                    margin="sm",
                    wrap=True
                ),
                FlexText(
                    text="請選擇您想查詢的穿搭時段：",
                    size="sm",
                    color="#999999",
                    align="center",
                    margin="md"
                ),
                FlexSeparator(margin="lg"),
                _outfit_button("☀️ 今日穿搭建議", "today"),
                _outfit_button("⏰ 即時穿搭建議", "current"),
                _outfit_button("📅 未來穿搭建議 (1-7天)", "forecast"),
                _other_location_button() # 加入查詢其他縣市按鈕
            ]
        )
    )

    return FlexMessage(
        alt_text="穿搭建議選單", # 訊息預覽文字
        contents=bubble
    )

# --- 範例使用方式 (假設在你的 Line Bot Webhook 處理函數中) ---

# from linebot.models import MessageEvent, TextMessage

# @handler.add(MessageEvent, message=TextMessage)
# def handle_message(event):
#     if event.message.text == "穿搭建議":
#         flex_message = get_single_outfit_suggestion_menu_flex_message()
#         line_bot_api.reply_message(event.reply_token, flex_message)
#     # ... 其他訊息處理邏輯