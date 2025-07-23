# life_reminders/outfit_flex_messages.py
import datetime

def build_today_outfit_flex(outfit_info: dict, location_name: str = "該地區") -> dict:
    """
    生成今日穿搭建議的 Flex Message 字典，只包含穿搭圖片和建議文字。
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

    # --- 計算並格式化當前日期、星期幾和時間（用於副標題） ---
    now = datetime.datetime.now() # 取得當前日期和時間

    # 格式化日期部分 (例如：2025年7月23日)
    try:
        specific_date_full = now.strftime("%Y年%-m月%-d日")
    except ValueError: # 對於可能不支援 %-m, %-d 的 Windows 系統
        specific_date_full = now.strftime("%Y年%m月%d日")

    # 取得中文星期幾 (例如：星期三)
    # %w 取得星期幾的數字，0是星期日，6是星期六
    weekday_str = now.strftime("%w")
    weekday_map = {
        "0": "日", "1": "一", "2": "二", "3": "三",
        "4": "四", "5": "五", "6": "六"
    }
    weekday_chinese = weekday_map.get(weekday_str, "")
    
    # 格式化時間部分 (例如：21:28)
    time_str = now.strftime("%H:%M")

    # 組合形成副標題文字
    subtitle_text = f"日期 : {specific_date_full} (星期{weekday_chinese}) {time_str}"

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
                    "size": "lg",
                    "align": "center",
                    "margin": "md",
                    "color": "#000000"
                },
                {
                    "type": "text",
                    "text": subtitle_text, # 副標題
                    "size": "sm", # 副標題字體較小
                    "color": "#666666",
                    "align": "center",
                    "margin": "none" # 緊跟主標題，無額外間距
                },
                {
                    "type": "separator",
                    "margin": "md" # 調整分隔線與上方/下方元件的間距
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "margin": "md",
                    "contents": suggestion_text_contents
                }
            ]
        }
    }