# life_reminders/forecast_outfit_flex_messages.py
import datetime

def build_forecast_outfit_card(outfit_info: dict, location_name: str, day_offset: int) -> dict:
    """
    生成單一未來穿搭建議的 Flex Message bubble (卡片)，包含穿搭圖片、建議文字和日期。
    Args:
        outfit_info (dict): 包含 'suggestion_text' 和 'suggestion_image_url' 的字典。
                            這個字典應該針對特定一天。
        location_name (str): 查詢的城市名稱，用於標題。
        day_offset (int): 相對於今天的日期偏移量 (0 代表今天, 1 代表明天, 以此類推)。
    Returns:
        dict: Flex Message 的單一 bubble 內容字典。
    """
    # 獲取建議文字列表，如果沒有則使用預設單句建議
    suggestions_list = outfit_info.get("suggestion_text", ["目前無法提供未來穿搭建議。"])
    if not isinstance(suggestions_list, list):
        suggestions_list = [str(suggestions_list)] # 強制轉換為列表中的字串

    # --- 計算並格式化日期和星期幾（用於副標題） ---
    forecast_date = datetime.date.today() + datetime.timedelta(days=day_offset)

    # 計算並格式化日期
    # 注意：這裡使用 fromisoformat() 或其他方式確保日期對象正確
    # 假設 outfit_info 中包含 'date_prefix' (今天/明天/日期) 和 'date_str' (2025年7月23日)
    # 從 outfit_info 中獲取已格式化的日期資訊
    # display_date_prefix = outfit_info.get("date_prefix", "")
    # display_date_str = outfit_info.get("date_str", "")
    
    # 為了確保日期的正確性，我們優先使用 outfit_info 中已經處理好的日期資訊
    # 如果 outfit_info 沒有，再使用 day_offset 計算（作為備用）
    """
    if not display_date_str:
        # 如果 outfit_info 沒有提供，則根據 day_offset 計算
        forecast_date = datetime.date.today() + datetime.timedelta(days=day_offset)
    """

    # 格式化完整日期字串，處理 Windows/Linux 差異
    try:
        specific_date_full = forecast_date.strftime("%Y年%-m月%-d日")
    except ValueError: # for Windows
        specific_date_full = forecast_date.strftime("%Y年%m月%d日")

    # 獲取星期幾 (考慮現在是 2025 年 7 月 23 日)
    weekday_str = forecast_date.strftime("%w") # %w gives day of week as a decimal, where 0 is Sunday and 6 is Saturday.
    weekday_map = {
        "0": "日", "1": "一", "2": "二", "3": "三",
        "4": "四", "5": "五", "6": "六"
    }
    weekday_chinese = weekday_map.get(weekday_str, "")

    # 組合副標題
    subtitle_text = f"日期 : {specific_date_full} (星期{weekday_chinese})"

    # 組合標題日期
    # title_date_text = f"📅 {location_name} {display_date_str}"

    """
    # 計算並格式化日期
    forecast_date = datetime.date.today() + datetime.timedelta(days=day_offset)
    # 這裡會根據執行時的當前日期動態生成，例如今天是 7/23，day_offset=1 就是 7/24
    date_str = forecast_date.strftime("%m/%d (%a)") # 例如: 07/24 (三)
    """

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
                    "text": f"📅 {location_name} 未來 7 天穿搭建議",
                    "weight": "bold",
                    "size": "lg",
                    "align": "center",
                    "margin": "md",
                    "color": "#000000"
                },
                {
                    "type": "text",
                    "text": subtitle_text, # 副標題
                    "size": "sm", # 副標題可以小一點
                    "color": "#666666",
                    "align": "center",
                    "margin": "none" # 緊跟主標題，不需要額外間距
                },
                {
                    "type": "separator",
                    "margin": "md" # 調整分隔線與上方/下方元件的間距
                },
                {   "type": "box", # 用一個 Box 包裹多個 Text 元件
                    "layout": "vertical",
                    "spacing": "sm", # 設定 Box 內元件間距
                    "margin": "md",
                    "contents": suggestion_text_contents
                }
            ]
        }
    }

def build_forecast_outfit_carousel(daily_outfit_data: list[dict], location_name: str = "該地區") -> dict:
    """
    生成未來穿搭建議的 Flex Message Carousel，包含多張穿搭卡片。
    Args:
        daily_outfit_data (list[dict]): 包含每天穿搭資訊的列表，每個字典包含
                                         'suggestion_text' 和 'suggestion_image_url'。
                                         列表的順序代表天數 (索引 0 為第 1 天)。
        location_name (str): 查詢的城市名稱，用於標題。
    Returns:
        dict: Flex Message 的 Carousel 內容字典。
              如果 daily_outfit_data 為空，返回一個包含單一預設 bubble 的 Carousel。
    """
    bubbles = []

    for day_offset, outfit_info in enumerate(daily_outfit_data[:7]):
        if not outfit_info or not outfit_info.get("suggestion_text"):
            continue
        bubble = build_forecast_outfit_card(outfit_info, location_name, day_offset)
        # 使用 day_offset = 0 來表示 "今天" 或 "目前"
        bubbles.append(bubble)

    if not bubbles:
        # 所有資料都不合法或空值
        default_outfit_info = {
            "suggestion_text": ["抱歉，目前沒有未來天氣的穿搭建議。"],
            "suggestion_image_url": "https://i.imgur.com/no_data_available.png"
        }
        bubbles.append(build_forecast_outfit_card(default_outfit_info, location_name, 0))

    return {
        "type": "carousel",
        "contents": bubbles
    }