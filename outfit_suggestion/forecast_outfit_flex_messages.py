# outfit_suggestion/forecast_outfit_flex_messages.py
import logging
from linebot.v3.messaging.models import FlexBubble, FlexBox, FlexText, FlexImage, FlexSeparator
from utils.flex_message_elements import make_kv_row

logger = logging.getLogger(__name__)

def build_forecast_outfit_card(outfit_info: dict, location_name: str, day_offset: int) -> FlexBubble:
    """
    根據提供的穿搭資訊和已經格式化好的天氣數據構建一個單天的 Flex Message 卡片（FlexBubble 物件）。

    Args:
        outfit_info (dict): 包含穿搭建議和已經格式化好的天氣顯示資訊的字典。
                            預期包含 'display_weather_desc', 'display_feels_like_temp', 
                            'display_pop', 'display_humidity', 'display_uv_index', 
                            以及 'suggestion_text', 'suggestion_image_url' 等。
        location_name (str): 城市名稱。
        day_offset (int): 從今天開始的天數偏移 (0=今天, 1=明天, etc.)。

    Returns:
        FlexBubble: LINE Flex Message 的 Bubble 元件物件。
    """
    # 獲取建議文字列表，如果沒有則使用預設單句建議
    suggestion_text = outfit_info.get("suggestion_text", ["目前無法提供未來穿搭建議。"])
    suggestion_image_url = outfit_info.get("suggestion_image_url", "https://i.imgur.com/default_forecast_outfit.png")
    # outfit_tags = outfit_info.get("outfit_tags", []) # 穿搭標籤列表

    date_full_formatted = outfit_info.get("obs_time", "日期 N/A") # 例如 "2025年07月23日 (三)"

    # 從 outfit_info 獲取 day_index，這個值在 forecast_flex_converter 中被設定為 i + 1
    display_day_index = outfit_info.get("day_index", day_offset + 1) # 預設使用 day_offset + 1

    # --- 計算並格式化日期和星期幾（用於副標題） ---
    # forecast_date = datetime.date.today() + datetime.timedelta(days=day_offset)

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
    """

    # 組合副標題 (日期和星期)
    subtitle_text = date_full_formatted
    # subtitle_text = f"日期：{specific_date_full} (星期{weekday_chinese})"

    # 組合標題日期
    # title_date_text = f"📅 {location_name} {display_date_str}"

    # 主標題：使用 day_index 動態顯示「未來第 X 天」
    title_text = f"📍 {location_name} 未來第 {display_day_index} 天穿搭建議"

    """
    # 計算並格式化日期
    forecast_date = datetime.date.today() + datetime.timedelta(days=day_offset)
    # 這裡會根據執行時的當前日期動態生成，例如今天是 7/23，day_offset=1 就是 7/24
    date_str = forecast_date.strftime("%m/%d (%a)") # 例如: 07/24 (三)
    """
    """
    display_date_only = "N/A"
    if date_full_formatted.startswith("日期："):
        display_date_only = date_full_formatted.replace("日期：", "")
    else:
        display_date_only = date_full_formatted # 如果不符合預期格式，就用原始的

    subtitle_text = display_date_only
    """

    # 創建一個列表，用於存放每個 FlexText 元件
    suggestion_text_contents = []
    for suggestion in suggestion_text:
        suggestion_text_contents.append(
            FlexText(
                text=suggestion,
                size="md",
                color="#333333",
                wrap=True,
                margin="sm",
                align="start"
                # 如果你希望每句話都粗體，可以在這裡加上 "weight": "bold"
            )
        )

    # --- 新增天氣資訊區塊內容 ---
    weather_info_contents = []

    # 直接使用 forecast_flex_converter.py 預先處理好的顯示字串
    # 這些鍵現在應該以 'display_' 開頭
    weather_info_contents.append(make_kv_row("天氣狀況：", outfit_info.get("display_weather_desc")))
    weather_info_contents.append(make_kv_row("體感溫度：", outfit_info.get("display_feels_like_temp")))
    weather_info_contents.append(make_kv_row("濕度：", outfit_info.get("display_humidity")))
    weather_info_contents.append(make_kv_row("降雨機率：", outfit_info.get("display_pop")))
    weather_info_contents.append(make_kv_row("紫外線指數：", outfit_info.get("display_uv_index")))
    
    # 你也可以選擇加入其他顯示資訊，例如風速和風向
    # weather_info_contents.append(make_kv_row("風速", outfit_info.get("display_wind_speed", "N/A")))
    # weather_info_contents.append(make_kv_row("風向", outfit_info.get("display_wind_dir", "N/A")))

    return FlexBubble(
        direction="ltr",
        hero=FlexBox(
            layout="vertical",
            contents=[
                FlexImage(
                    url=suggestion_image_url, 
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
                    text=title_text,
                    weight="bold",
                    size="lg",
                    align="center",
                    margin="md",
                    color="#000000"
                ),
                FlexText(
                    text=subtitle_text,
                    size="sm",
                    color="#666666",
                    align="center",
                    margin="none"
                ),
                FlexSeparator(margin="md"),
                FlexBox(
                    layout="vertical",
                    spacing="sm",
                    margin="md",
                    contents=weather_info_contents # 這裡直接放入 FlexBox 物件列表
                ),
                FlexSeparator(margin="md"),
                FlexBox(
                    layout="vertical",
                    spacing="sm",
                    margin="md",
                    contents=suggestion_text_contents # 這裡直接放入 FlexText 物件列表
                )
            ]
        )
    )