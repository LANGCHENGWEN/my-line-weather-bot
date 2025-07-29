# forecast_options_flex.py
"""
建立「請選擇要查幾天預報」Flex Message
"""

from linebot.v3.messaging.models import (
    FlexMessage, FlexBubble, FlexBox,
    FlexText, FlexButton, FlexSeparator, PostbackAction
)

# ---------- 主要函式 ----------
def create_forecast_options_flex_message(
        default_county: str, # 用於天數選單頂部顯示的預設城市
        target_query_city: str # 用於 Postback action 中實際查詢的目標城市
) -> FlexMessage:
    """
    回傳一張 FlexMessage，裡面有 3 / 5 / 7 天預報的按鈕。

    Args:
        county   (str): 縣市，如「臺中市」
        township (str): 鄉鎮市區，如「北區」
    """
    def _day_btn(days: int) -> FlexButton:
        return FlexButton(
            action=PostbackAction(
                label=f"{days} 天預報",
                data=f"action=forecast_days&days={days}&city={target_query_city}"
            ),
            style="primary",
            color="#00B900",   # LINE 綠
            height="sm",
            margin="md"
        )
    
    def _other_location_btn() -> FlexButton:
        return FlexButton(
            action=PostbackAction(
                type="postback",
                label="查詢其他縣市",
                data="action=forecast_other_city",
            ),
            style="secondary",
            color="#AAAAAA",
            height="sm",
            margin="lg"
        )

    bubble = FlexBubble(
        body=FlexBox(
            layout="vertical",
            spacing="md",
            contents=[
                FlexText(
                    text=f"您目前的預設城市是 {default_county}。",
                    weight="bold",
                    size="md",
                    wrap=True
                ),
                FlexText(
                    text="請選擇想查詢的天數：",
                    size="md",
                    wrap=True,
                    margin="md"
                ),
                FlexSeparator(margin="md"),
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