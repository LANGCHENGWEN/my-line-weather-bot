# utils/flex_message_elements.py
"""
輔助模組，專門用於建立 LINE Flex Message 的常用 UI 元件。
將重複、模式化的 Flex Message 結構抽象化為簡單易用的函式。
其他模組（例如即時天氣與未來預報的 Flex Message）不需要重複編寫複雜的 FlexBox 和 FlexText 結構。
"""
from typing import Any
from linebot.v3.messaging.models import FlexBox, FlexText

def make_kv_row(label: str, value: Any) -> FlexBox:
    """
    建立一個由標籤（label）和值（value）組成的 Flex Message 橫向排版區塊。
    將傳入的鍵值對 (`label`, `value`) 渲染為一行兩個不同顏色的文字。
    """
    # --- 確保 value 在傳遞給 FlexText 前被轉換為字串 ---
    # FlexText 的 `text` 參數要求字串類型，這個防護性檢查確保即使傳入 `None` 或其他非字串類型，程式也不會因為類型錯誤而崩潰
    display_value = str(value) if value is not None else "無資料"

    # --- 建立並返回 FlexBox 物件 ---
    return FlexBox(
        layout="baseline", # 確保兩側文字的基線對齊，讓排版看起來更整齊
        spacing="sm",      # 設定兩個文字之間的間距為小
        contents=[
            FlexText(
                text=label,
                color="#4169E1", # 藍色
                size="md",
                flex=4             # 佔據較小的空間
            ),
            FlexText(
                text=display_value, # 使用已轉換為字串的值
                wrap=True,          # 確保文字在超出範圍時自動換行
                color="#8A2BE2",  # 紫色
                size="md",
                flex=5              # 佔據較大的空間
            )
        ]
    )