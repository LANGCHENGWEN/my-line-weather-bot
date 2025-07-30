# utils/flex_templates.py
from linebot.v3.messaging.models import FlexBox, FlexText, FlexBubble, FlexMessage, FlexContainer

def build_hello_flex() -> FlexMessage:
    """
    使用 LINE Flex Message SDK 建構一個歡迎 Flex Message。
    """
    hello_bubble_content = FlexBubble(
        body=FlexBox(
            layout="vertical",
            spacing="md",
            contents=[
                FlexText(
                    text="哈囉！您好～ 我是暖心天氣語",
                    weight="bold",
                    size="lg",
                    wrap=True
                ),
                FlexText(
                    text="您可以先設定預設城市，然後點擊選單，我會告訴您天氣資訊和穿搭建議喔！",
                    wrap=True,
                    margin="sm",
                    size="md"
                ),
                FlexText(
                    text="🌟 請輸入您想預設的城市名稱，例如「台中市」或「台北市」，讓我幫您設定預設城市吧！",
                    wrap=True,
                    margin="md",
                    size="md",
                    color="#555555"
                )
            ]
        )
    )

    # 將 FlexBubble 包裹在 FlexMessage 中，並提供 alt_text
    return FlexMessage(
        alt_text="歡迎使用暖心天氣語 ～", # 這是一個必須的參數
        contents=hello_bubble_content # 這裡傳入上面定義的 FlexBubble 物件
    )