# outfit_flex_messages.py
from linebot.v3.messaging import PostbackAction
from linebot.v3.messaging.models import (
    FlexBox, FlexText, FlexMessage, FlexBubble,
    FlexButton, FlexSeparator, ImageComponent
)

def get_single_outfit_suggestion_menu_flex_message():
    """
    生成一個單一 Flex Message 卡片選單，包含今日、即時、未來穿搭建議選項。
    """
    flex_message_content = FlexBubble(
        direction='ltr', # 內容排列方向，ltr是從左到右
        hero=FlexBox( # 頂部圖片區塊 (可選，如果不需要可以移除)
            layout='vertical',
            contents=[
                ImageComponent(
                    url="https://i.imgur.com/your_outfit_menu_banner.png", # 請替換成你菜單的橫幅圖片 URL
                    size='full',
                    aspect_ratio='20:9', # 圖片比例
                    aspect_mode='cover'
                )
            ]
        ),
        body=FlexBox(
            layout='vertical',
            contents=[
                FlexText(
                    text="👗 穿搭建議 👔",
                    weight='bold',
                    size='xl',
                    align='center',
                    margin='md'
                ),
                FlexText(
                    text="請選擇您想查詢的穿搭類型：",
                    size='sm',
                    color='#999999',
                    align='center',
                    margin='md'
                ),
                FlexSeparator(margin='lg'), # 分隔線
                FlexButton(
                    style='link', # 連結樣式按鈕
                    height='sm',
                    action=PostbackAction(label="☀️ 今日穿搭建議", data="action=outfit_today")
                ),
                FlexSeparator(margin='md'),
                FlexButton(
                    style='link',
                    height='sm',
                    action=PostbackAction(label="⏰ 即時穿搭建議", data="action=outfit_current")
                ),
                FlexSeparator(margin='md'),
                FlexButton(
                    style='link',
                    height='sm',
                    action=PostbackAction(label="📅 未來穿搭建議 (3-7天)", data="action=outfit_forecast")
                )
            ]
        ),
        footer=FlexBox( # 底部資訊區塊 (可選，如果不需要可以移除)
            layout='vertical',
            contents=[
                FlexText(
                    text="點擊選項即可查詢",
                    size='xs',
                    color='#aaaaaa',
                    align='center'
                )
            ]
        )
    )

    flex_message = FlexMessage(alt_text="請選擇穿搭建議類型", contents=flex_message_content)
    return flex_message

# --- 範例使用方式 (假設在你的 Line Bot Webhook 處理函數中) ---

# from linebot.models import MessageEvent, TextMessage

# @handler.add(MessageEvent, message=TextMessage)
# def handle_message(event):
#     if event.message.text == "穿搭建議":
#         flex_message = get_single_outfit_suggestion_menu_flex_message()
#         line_bot_api.reply_message(event.reply_token, flex_message)
#     # ... 其他訊息處理邏輯