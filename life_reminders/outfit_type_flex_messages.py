# outfit_type_flex_messages.py
from linebot.v3.messaging import PostbackAction
from linebot.v3.messaging.models import (
    FlexBox, FlexText, FlexBubble,
    FlexButton, FlexSeparator, FlexImage
)

def build_outfit_suggestions_flex() -> dict:
    """
    生成一個單一 Flex Message 卡片選單，包含今日、即時、未來穿搭建議選項。
    返回的是可以直接用來構建 FlexMessage 的 JSON 字典。
    """
    flex_message_content = {
        "type": "bubble",
        "direction": "ltr",
        "hero": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "image",
                    "url": "https://i.imgur.com/your_outfit_menu_banner.png", # 請替換成你菜單的橫幅圖片 URL
                    "size": "full",
                    "aspectRatio": "20:9",
                    "aspectMode": "cover"
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "👗 穿搭建議 👔",
                    "weight": "bold",
                    "size": "xl",
                    "align": "center",
                    "margin": "md"
                },
                {
                    "type": "text",
                    "text": "請選擇您想查詢的穿搭類型：",
                    "size": "sm",
                    "color": "#999999",
                    "align": "center",
                    "margin": "md"
                },
                {
                    "type": "separator",
                    "margin": "lg"
                },
                {
                    "type": "button",
                    "style": "link",
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": "☀️ 今日穿搭建議",
                        "data": "action=outfit_query&type=today"
                    }
                },
                {
                    "type": "separator",
                    "margin": "md"
                },
                {
                    "type": "button",
                    "style": "link",
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": "⏰ 即時穿搭建議",
                        "data": "action=outfit_query&type=current"
                    }
                },
                {
                    "type": "separator",
                    "margin": "md"
                },
                {
                    "type": "button",
                    "style": "link",
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": "📅 未來穿搭建議 (3-7天)",
                        "data": "action=outfit_query&type=forecast"
                    }
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "點擊選項即可查詢",
                    "size": "xs",
                    "color": "#aaaaaa",
                    "align": "center"
                }
            ]
        }
    }
    return flex_message_content

# --- 範例使用方式 (假設在你的 Line Bot Webhook 處理函數中) ---

# from linebot.models import MessageEvent, TextMessage

# @handler.add(MessageEvent, message=TextMessage)
# def handle_message(event):
#     if event.message.text == "穿搭建議":
#         flex_message = get_single_outfit_suggestion_menu_flex_message()
#         line_bot_api.reply_message(event.reply_token, flex_message)
#     # ... 其他訊息處理邏輯