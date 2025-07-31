# life_reminders/weekend_weather_flex.py
import json
import logging
from typing import Any, Dict, List, Optional
from linebot.v3.messaging.models import (
    Message, FlexBox, FlexText, FlexImage, FlexBubble, FlexMessage, FlexSeparator, FlexCarousel 
)
from utils.flex_message_elements import make_kv_row # 假設 make_kv_row 函數在 utils.flex_message_elements 中

logger = logging.getLogger(__name__)

def build_weekend_weather_flex(outfit_info: dict, day_data: Dict[str, Any], county_name: str) -> Optional[FlexBubble]:
    """
    根據單日週末天氣資料建立 Flex Bubble。

    Args:
        day_data (Dict[str, Any]): 包含單日天氣資訊的字典。
        county_name (str): 查詢的縣市名稱。

    Returns:
        Optional[FlexBubble]: 構建好的 FlexBubble，如果數據不完整，返回 None。
    """
    if not day_data:
        logger.warning("沒有可用的單日週末天氣預報數據。")
        return None
    
    # 獲取建議文字列表，如果沒有則使用預設單句建議
    suggestion_text = outfit_info.get("suggestion_text", ["目前無法提供未來穿搭建議。"])
    suggestion_image_url = outfit_info.get("suggestion_image_url", "https://i.imgur.com/default_forecast_outfit.png")

    # date_full_formatted = outfit_info.get("obs_time", "日期 N/A") # 例如 "2025年07月23日 (三)"

    # logger.debug(f"🧪 傳入 Flex (週末單日) 的資料: {json.dumps(day_data, ensure_ascii=False, indent=2)}")

    # 每個 Bubble 的標題包含縣市和日期 (例如: 📍 臺中市 07/26 (六))
    # title_text = f"📍 {county_name} {day_data.get('date_formatted', '未知日期')}"

    # 新標題：縣市名稱 週末天氣
    main_title = f"📍 {county_name} 週末天氣"
    # 新副標題：日期
    date_subtitle = day_data.get('date_formatted', '未知日期')
    # date_subtitle = date_full_formatted

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
        
    # 構建單日天氣資訊的 FlexBox 內容
    flex_bubble_object = FlexBubble(
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
                    text=main_title,
                    color="#000000",
                    weight="bold",
                    size="lg",
                    margin="md",
                    align="center"
                ),
                FlexText(
                        text=date_subtitle,
                        size="sm",
                        color="#666666",
                        align="center",
                        margin="none"
                    ),
                FlexSeparator(margin="md"),
                FlexBox(
                    layout="vertical",
                    margin="lg",
                    spacing="sm",
                    contents=[
                        make_kv_row("🌈 天氣狀況：", day_data.get("display_weather_desc", "N/A")),
                        FlexBox(
                            layout="vertical",
                            spacing="sm",
                            contents=[
                                make_kv_row("🌡️ 最高溫度：", day_data.get("display_max_temp", "N/A")),
                                make_kv_row("❄️ 最低溫度：", day_data.get("display_min_temp", "N/A")),
                                make_kv_row("    (體感：", f"{day_data.get('display_feels_like_temp', 'N/A')})") # 體感溫度已格式化為 "X~Y度)"
                            ]
                        ),
                        make_kv_row("💧 濕度：", day_data.get("display_humidity", "N/A")),
                        make_kv_row("🌧️ 降雨機率：", day_data.get("display_pop", "N/A")),
                        make_kv_row("🌬️ 風速：", day_data.get("display_wind_speed", "N/A")),
                        make_kv_row("☀️ 紫外線指數:", day_data.get("display_uv_index", "N/A"))
                    ]
                ),
                FlexSeparator(margin="md"),
                FlexBox(
                    layout="vertical",
                    spacing="sm",
                    margin="md",
                    contents=suggestion_text_contents # 這裡直接放入 FlexText 物件列表
                ),
                FlexSeparator(margin="md"), # 在引導文字前再加一個分隔線，增加區隔
                FlexText(
                    text="💡 查詢其他縣市，請點選「未來預報」。",
                    size="sm",
                    color="#999999", # 較淺的顏色，表示是提示資訊
                    wrap=True,
                    margin="md",
                    align="center"
                )
            ]
        )
    )
    return flex_bubble_object # 直接回傳已經構建好的 FlexBubble 物件