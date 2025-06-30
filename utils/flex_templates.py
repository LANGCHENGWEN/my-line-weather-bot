# utils/flex_templates.py
from linebot.v3.messaging.models import FlexMessage, FlexContainer

# ① 把你提供的 Bubble JSON 放進字典
HELLO_BUBBLE = {
    "type": "bubble",
    "body": {
        "type": "box",
        "layout": "vertical",
        "spacing": "md",
        "contents": [
            {
                "type": "text",
                "text": "哈囉！您好～我是暖心天氣語",
                "weight": "bold",
                "size": "lg",
                "wrap": True
            },
            {
                "type": "text",
                "text": "您可以先設定預設城市，然後點擊選單，我會告訴您天氣資訊和穿搭建議喔！",
                "wrap": True,
                "margin": "sm",
                "size": "md"
            },
            {
                "type": "text",
                "text": "請輸入您想預設的城市名稱，例如「台中市」或「台北市」，讓我幫您設定預設城市吧！",
                "wrap": True,
                "margin": "md",
                "size": "md",
                "color": "#555555"
            }
        ]
    }
}

# ② 包裝成函式，回傳 FlexMessage 物件
def build_hello_flex() -> FlexMessage:
    container = FlexContainer.from_dict(HELLO_BUBBLE)
    return FlexMessage(
        alt_text="歡迎使用暖心天氣語",
        contents=container
    )