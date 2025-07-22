# life_reminders/outfit_flex_messages.py
from linebot.v3.messaging.models import (
    FlexBox, FlexText, FlexBubble,
    FlexButton, FlexSeparator, FlexImage
)

def build_today_outfit_flex(outfit_info: dict, location_name: str = "該地區") -> dict:
    """
    生成未來穿搭建議的 Flex Message 字典，只包含穿搭圖片和建議文字。
    Args:
        outfit_info (dict): 包含 'suggestion_text' 和 'suggestion_image_url' 的字典。
        location_name (str): 查詢的城市名稱，用於標題。
    Returns:
        dict: Flex Message 的內容字典。
    """
    # 獲取建議文字列表，如果沒有則使用預設單句建議
    suggestions_list = outfit_info.get("suggestion_text", ["目前無法提供即時穿搭建議。"])

    # 創建一個列表，用於存放每個 FlexText 元件
    suggestion_text_contents = []
    for suggestion in suggestions_list:
        suggestion_text_contents.append({
            "type": "text",
            "text": suggestion,
            "size": "md",
            "color": "#333333",
            "wrap": True,
            "margin": "sm", # 將 margin 設為 sm 或 none，讓行距不會太大
            "align": "center"
            # 如果你希望每句話都粗體，可以在這裡加上 "weight": "bold"
        })

    return {
        "type": "bubble",
        "direction": "ltr",
        "hero": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "image",
                    "url": outfit_info.get("suggestion_image_url", "https://i.imgur.com/default_forecast_outfit.png"), # 預設圖
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
                    "text": f"☀️ {location_name} 今日穿搭建議",
                    "weight": "bold",
                    "size": "xl",
                    "align": "center",
                    "margin": "md",
                    "color": "#000000"
                },
                {
                    "type": "box", # 用一個 Box 包裹多個 Text 元件
                    "layout": "vertical",
                    "spacing": "sm", # 設定 Box 內元件間距
                    "margin": "md",
                    "contents": suggestion_text_contents
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
                        "label": "返回穿搭選單",
                        "data": "action=outfit_advisor"
                    }
                }
            ]
        }
    }

def build_current_outfit_flex(outfit_info: dict, location_name: str = "該地區") -> dict:
    """
    生成即時穿搭建議的 Flex Message 字典，包含穿搭圖片和建議文字（多行顯示）。
    Args:
        outfit_info (dict): 包含 'suggestion_text' 和 'suggestion_image_url' 的字典。
        location_name (str): 查詢的城市名稱，用於標題。
    Returns:
        dict: Flex Message 的內容字典。
    """
    # 獲取建議文字列表，如果沒有則使用預設單句建議
    suggestions_list = outfit_info.get("suggestion_text", ["目前無法提供即時穿搭建議。"])

    # 創建一個列表，用於存放每個 FlexText 元件
    suggestion_text_contents = []
    for suggestion in suggestions_list:
        suggestion_text_contents.append({
            "type": "text",
            "text": suggestion,
            "size": "md",
            "color": "#333333",
            "wrap": True,
            "margin": "sm", # 將 margin 設為 sm 或 none，讓行距不會太大
            "align": "center"
            # 如果你希望每句話都粗體，可以在這裡加上 "weight": "bold"
        })

    return {
        "type": "bubble",
        "direction": "ltr",
        "hero": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "image",
                    "url": outfit_info.get("suggestion_image_url", "https://i.imgur.com/default_outfit.png"), # 預設圖
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
                    "text": f"⏰ {location_name} 即時穿搭建議",
                    "weight": "bold",
                    "size": "xl",
                    "align": "center",
                    "margin": "md",
                    "color": "#000000"
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "margin": "md",
                    "contents": suggestion_text_contents
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
                        "label": "返回穿搭選單",
                        "data": "action=outfit_advisor"
                    }
                }
            ]
        }
    }

def build_forecast_outfit_flex(outfit_info: dict, location_name: str = "該地區") -> dict:
    """
    生成未來穿搭建議的 Flex Message 字典，只包含穿搭圖片和建議文字。
    Args:
        outfit_info (dict): 包含 'suggestion_text' 和 'suggestion_image_url' 的字典。
        location_name (str): 查詢的城市名稱，用於標題。
    Returns:
        dict: Flex Message 的內容字典。
    """
    # 獲取建議文字列表，如果沒有則使用預設單句建議
    suggestions_list = outfit_info.get("suggestion_text", ["目前無法提供即時穿搭建議。"])

    # 創建一個列表，用於存放每個 FlexText 元件
    suggestion_text_contents = []
    for suggestion in suggestions_list:
        suggestion_text_contents.append({
            "type": "text",
            "text": suggestion,
            "size": "md",
            "color": "#333333",
            "wrap": True,
            "margin": "sm", # 將 margin 設為 sm 或 none，讓行距不會太大
            "align": "center"
            # 如果你希望每句話都粗體，可以在這裡加上 "weight": "bold"
        })

    return {
        "type": "bubble",
        "direction": "ltr",
        "hero": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "image",
                    "url": outfit_info.get("suggestion_image_url", "https://i.imgur.com/default_forecast_outfit.png"), # 預設圖
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
                    "text": f"📅 {location_name} 未來穿搭建議 (3-7天)",
                    "weight": "bold",
                    "size": "xl",
                    "align": "center",
                    "margin": "md",
                    "color": "#000000"
                },
                {"type": "box", # 用一個 Box 包裹多個 Text 元件
                    "layout": "vertical",
                    "spacing": "sm", # 設定 Box 內元件間距
                    "margin": "md",
                    "contents": suggestion_text_contents
                },
                {
                    "type": "separator",
                    "margin": "lg"
                },
                {
                    "type": "button",
                    "style": "link",
                    "height": "sm",
                    "action": { # <--- 修改點: 將 PostbackAction 物件替換為字典
                        "type": "postback",
                        "label": "返回穿搭選單",
                        "data": "action=outfit_advisor"
                    }
                }
            ]
        }
    }