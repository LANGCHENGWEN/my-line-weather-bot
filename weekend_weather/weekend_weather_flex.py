# weekend_weather/weekend_weather_flex.py
"""
根據「單一週末日期」的天氣和穿搭建議數據，動態生成一個 Flex Message 的「氣泡」（FlexBubble）。
主要職責：
1. 結構化內容：使用 Flex Message 的各種元件（`FlexBox`、`FlexText`、`FlexImage` 等），按照預設的佈局組織資訊。
2. 數據綁定：將傳入的天氣數據和穿搭建議（包括圖片 URL 和文字）精確的填入對應的 Flex 元件中。
3. 客製化呈現：根據數據的特性（例如建議文字的多寡），動態生成 Flex 元件列表。
4. 錯誤防護：在數據不完整時，提供預設值或返回 None，確保程式不會因為數據缺失而崩潰。
"""
import logging
from typing import Any, Dict, Optional
from linebot.v3.messaging.models import (
    FlexBox, FlexText, FlexImage, FlexBubble, FlexSeparator
)

from utils.flex_message_elements import make_kv_row

logger = logging.getLogger(__name__)

def build_weekend_weather_flex(outfit_info: dict, day_data: Dict[str, Any], county_name: str) -> Optional[FlexBubble]:
    """
    根據單日週末天氣資料建立一個 Flex Message 氣泡。
    將所有必要的資訊（天氣數據、穿搭建議）作為輸入，並組裝成一個完整的 FlexBubble 物件。

    Args:
        outfit_info (dict): 包含穿搭建議文字和圖片 URL 的字典。
        day_data (Dict[str, Any]): 包含單日天氣資訊的字典。
        county_name (str): 查詢的縣市名稱。

    Returns:
        Optional[FlexBubble]: 構建好的 FlexBubble，如果數據不完整，返回 None。
    """
    # 數據有效性檢查，如果數據為空，立即返回 `None`
    if not day_data:
        logger.warning("沒有可用的單日週末天氣預報數據。")
        return None

    # --- 從傳入的 `outfit_info` 字典中，安全的獲取穿搭建議文字和圖片 URL ---
    # 使用 `.get()` 方法，並為每個鍵提供預設值，這樣即使在 `outfit_info` 字典中缺少某些鍵，程式也不會報錯，而是會使用預設的圖片或文字
    # 確保在任何情況下都能回傳一個有效的 Flex Message，提高程式的穩定性
    suggestion_text = outfit_info.get("suggestion_text", ["目前無法提供週末穿搭建議。"])
    suggestion_image_url = outfit_info.get("suggestion_image_url", "https://i.postimg.cc/T3qs1kMf/NO_DATA.png")

    # --- 組合主標題 ---
    main_title = f"📍 {county_name} 週末天氣"

    # --- 組合副標題 (日期和星期) ---
    # 直接使用 `day_data` 中已經處理好的格式化日期字串
    date_subtitle = day_data.get('date_formatted')

    # --- 創建一個穿搭建議的文字列表，用於存放每個 FlexText 元件 ---
    """
    將穿搭建議的文字列表 `suggestion_text` 轉換為一系列的 `FlexText` 物件。
    因為 Flex Message 的內容元件需要是特定的物件（如 `FlexText`）。
    透過迴圈，為每一條建議文字都生成一個獨立的 `FlexText` 物件，並將其加入列表，以便後續的 `FlexBox` 佈局使用。
    """
    suggestion_text_contents = []
    for suggestion in suggestion_text:
        suggestion_text_contents.append(
            FlexText(
                text=suggestion,
                size="md",
                color="#333333",
                wrap=True, # 確保文字在超出範圍時自動換行
                margin="sm",
                align="start"
            )
        )

    # --- 構建 Flex Bubble ---
    """
    使用 `FlexBubble` 作為最外層的容器，包含了 `hero`（頂部圖片）和 `body`（內容區）兩個部分。

    `hero` 區塊放置代表穿搭建議的圖片。
    `body` 區塊使用 `FlexBox` 佈局，從上到下依次放置標題、副標題、分隔線、天氣資訊區塊，以及穿搭建議文字區塊和提示文字，形成一個完整且美觀的週末天氣與穿搭卡片。
    """
    flex_bubble_object = FlexBubble(
        direction="ltr",
        hero=FlexBox(
            layout="vertical", # 內容垂直排列
            # --- 圖片 ---
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
                # --- 標題 ---
                FlexText(
                    text=main_title,
                    color="#000000",
                    weight="bold", # 粗體
                    size="lg",
                    margin="md",
                    align="center" # 置中對齊
                ),
                # --- 觀測時間 ---
                FlexText(
                        text=date_subtitle,
                        size="sm",
                        color="#666666",
                        align="center",
                        margin="none"
                    ),
                FlexSeparator(margin="md"), # 分隔線
                # --- 天氣資訊 ---
                FlexBox(
                    layout="vertical",
                    margin="lg",
                    spacing="sm", # 行與行之間有小間距
                    contents=[
                        make_kv_row("🌈 天氣狀況：", day_data.get("display_weather_desc")),
                        FlexBox(
                            layout="vertical",
                            spacing="sm",
                            contents=[
                                make_kv_row("🌡️ 最高溫度：", day_data.get("display_max_temp")),
                                make_kv_row("❄️ 最低溫度：", day_data.get("display_min_temp")),
                                make_kv_row("    (體感：", f"{day_data.get('display_feels_like_temp')})")
                            ]
                        ),
                        make_kv_row("💧 濕度：", day_data.get("display_humidity")),
                        make_kv_row("🌧️ 降雨機率：", day_data.get("display_pop")),
                        make_kv_row("🌬️ 風速：", day_data.get("display_wind_speed")),
                        make_kv_row("☀️ 紫外線指數:", day_data.get("display_uv_index"))
                    ]
                ),
                FlexSeparator(margin="md"),
                # --- 穿搭建議 ---
                FlexBox(
                    layout="vertical",
                    spacing="sm",
                    margin="md",
                    contents=suggestion_text_contents
                ),
                FlexSeparator(margin="md"),
                # --- 提示文字 ---
                FlexText(
                    text="💡 查詢其他縣市，請點選「未來預報」。",
                    size="sm",
                    color="#999999",
                    wrap=True,
                    margin="md",
                    align="center"
                )
            ]
        )
    )
    return flex_bubble_object