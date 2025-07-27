# utils/flex_message_elements.py
from typing import Any
from linebot.v3.messaging.models import FlexBox, FlexText

# ———— 小工具：快速做兩欄 Key‑Value row ————
def make_kv_row(label: str, value: Any) -> FlexBox:
    # 確保 value 在傳遞給 FlexText 前被轉換為字串
    display_value = str(value) if value is not None else "N/A"

    return FlexBox(
        layout="baseline",
        spacing="sm",
        contents=[
            FlexText(
                text=label,
                color="#4169E1", # 藍色
                size="md",
                flex=4
            ),
            FlexText(
                text=display_value, # 使用已轉換為字串的值
                wrap=True,
                color="#8A2BE2", # 紫色
                size="md",
                flex=5
            )
        ]
    )