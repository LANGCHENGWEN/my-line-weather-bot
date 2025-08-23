# weather_forecast/forecast_options_flex.py
"""
建立 LINE Flex Message 為用戶提供天氣預報天數的選擇介面。
生成一個氣泡卡片，其中包含三個主要功能：
1. 顯示用戶的預設城市，讓用戶知道目前查詢的目標地點。
2. 提供「3 天」、「5 天」和「7 天」預報的按鈕選項。
3. 提供一個「查詢其他縣市」的按鈕，引導用戶進入另一個對話流程。
"""
from linebot.v3.messaging.models import (
    FlexBox, FlexText, FlexBubble, FlexButton,
    FlexMessage, FlexSeparator, PostbackAction
)

def create_forecast_options_flex_message (default_county: str, target_query_city: str) -> FlexMessage:
    """
    根據預設城市和目標查詢城市，建立一個包含天氣預報天數選項的 Flex Message。
    生成一個獨立的 Flex Bubble，並嵌入不同的按鈕，每個按鈕都帶有不同的 Postback 數據，以便後續的事件處理程式可以根據這些數據來執行相應的查詢。

    Args:
        default_county (str): 天數選單頂部顯示的預設城市。
        target_query_city (str): Postback action 中實際查詢的目標城市。
    
    Returns:
        FlexMessage: 一個完整的 LINE Flex Message 物件，包含一個 Bubble。
    """
    # -- 內部輔助函式：建立天數按鈕 ---
    """
    這個函式是為了避免重複寫同樣的程式碼而設計的。
    接收一個 `days` 參數，並動態生成一個 PostbackAction 按鈕。
    Postback 的 `data` 字串包含所有必要資訊：`action=forecast_days`（動作類型）、`days={days}`（選擇的天數）以及 `city={target_query_city}`（要查詢的城市）。
    """
    def _day_btn(days: int) -> FlexButton:
        return FlexButton(
            action=PostbackAction(
                label=f"{days} 天預報",
                data=f"action=forecast_days&days={days}&city={target_query_city}"
            ),
            style="primary",
            color="#00B900",
            height="sm",
            margin="md"
        )
    
    # --- 內部輔助函式：建立查詢其他縣市按鈕 ---
    """
    這個函式創建一個單獨的按鈕，用於讓用戶啟動「查詢其他縣市」的對話流程。
    Postback 的 `data` 僅包含 `action=forecast_other_city`，主程式會根據這個動作來判斷，並引導用戶輸入新的城市名稱。
    這個按鈕使用灰色來與主要的綠色天數按鈕區分開來。
    """
    def _other_location_btn() -> FlexButton:
        return FlexButton(
            action=PostbackAction(
                type="postback",
                label="查詢其他縣市",
                data="action=forecast_other_city"
            ),
            style="secondary",
            color="#AAAAAA",
            height="sm",
            margin="lg"
        )

    # --- 建構 Flex Bubble 物件 ---
    bubble = FlexBubble(
        body=FlexBox(
            layout="vertical", # 內容垂直排列
            spacing="md",
            contents=[
                FlexText(
                    text=f"您目前的預設城市是 {default_county}。",
                    weight="bold", # 粗體
                    size="md",
                    wrap=True      # 確保文字在超出範圍時自動換行
                ),
                FlexText(
                    text="請選擇想查詢的天數：",
                    size="md",
                    wrap=True,
                    margin="md"
                ),
                FlexSeparator(margin="md"), # 分隔線
                _day_btn(3),
                _day_btn(5),
                _day_btn(7),
                _other_location_btn()
            ]
        )
    )

    return FlexMessage(
        alt_text=f"{default_county} 天氣預報：請選擇天數",
        contents=bubble
    )