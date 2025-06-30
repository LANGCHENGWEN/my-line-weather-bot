# -*- coding: utf-8 -*-
"""
建立「請選擇要查幾天預報」Flex Message
"""

from linebot.v3.messaging.models import (
    FlexMessage,
    FlexBubble,
    FlexBox,
    FlexText,
    FlexButton,
    FlexSeparator,
    PostbackAction,
)

# ---------- 主要函式 ----------
def create_forecast_options_flex_message(county: str, township: str) -> FlexMessage:
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
                data=f"action=get_forecast&county={county}&township={township}&days={days}",
                display_text=f"正在查詢 {county}{township} 的 {days} 天天氣預報…",
            ),
            style="primary",
            color="#00B900",   # LINE 綠
            height="sm",
            margin="md",
        )

    bubble = FlexBubble(
        body=FlexBox(
            layout="vertical",
            spacing="md",
            contents=[
                FlexText(
                    text="請選擇想查詢的天數：",
                    weight="bold",
                    size="md",
                    wrap=True,
                ),
                FlexSeparator(margin="md"),
                _day_btn(3),
                _day_btn(5),
                _day_btn(7),
            ],
        )
    )

    return FlexMessage(
        alt_text=f"{county}{township} 天氣預報：請選擇天數",
        contents=bubble,
    )