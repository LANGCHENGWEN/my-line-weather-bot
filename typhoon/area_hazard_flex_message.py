# typhoon/area_hazard_flex_message.py
"""
將已經過解析和格式化的「中央氣象署地區影響預警」數據，轉換為 LINE Flex Message 的視覺化呈現。
主要作用：
1. 統一介面外觀：提供一個 `create_area_hazard_flex_message` 函式，確保所有地區影響預警的訊息都有一致且美觀的視覺樣式。
2. 數據到 UI 的轉換：將包含預警標題、發布時間、影響地區和詳細說明的 Python 字典，精準的映射到 Flex Message 的不同 UI 元件，如 `FlexText` 和 `FlexBox`。
3. 處理多個預警：根據傳入的預警數量，選擇返回單個 `FlexBubble` 或包含多個 `FlexBubble` 的 `FlexCarousel`，以適應不同情境。
"""
import logging
from typing import Any, List, Dict, Optional

from linebot.v3.messaging.models import (
    Message, FlexBox, FlexText, FlexBubble,
    FlexMessage, FlexCarousel, FlexSeparator
)

logger = logging.getLogger(__name__)

# --- 小工具：用於創建一個包含「標籤（label）」和「值（Value）」的水平佈局 FlexBox ---
def make_kv_row_area_hazard(label: str, value: str) -> FlexBox:
    """
    避免在主函式中重複撰寫相同的 FlexBox 結構，讓程式碼更簡潔、更易於維護。
     
    Args:
        label (str): 資訊的標籤，例如 "發布時間"。
        value (str): 資訊的具體內容，預期是一個已格式化好的字串。
     
    Returns:
        FlexBox: 包含標籤和值的 FlexBox 物件。
    """
    return FlexBox(
        layout="horizontal",
        spacing="sm",
        contents=[
            FlexText(
                text=str(label),
                color="#4169E1",
                size="md",
                flex=0,
                weight="bold",
                align="start"
            ),
            FlexText(
                text=str(value) if value is not None else "未知時間",
                wrap=True,
                color="#333333",
                size="md",
                flex=1,
                margin="sm"
            )
        ],
        alignItems="flex-start"
    )

# --- 根據一個包含多個預警資訊的列表，動態建構 Flex Message ---
def create_area_hazard_flex_message(warnings: List[Dict[str, Any]]) -> Optional[Message]:
    """
    1. 遍歷每一個預警，並為每個預警建立一個獨立的 Flex Bubble。
    2. 每個 Bubble 都會根據預警的標題、時間、地區和說明等資訊進行排版。
    3. 最後根據生成的 Bubble 數量，決定是返回單個 `FlexMessage` 還是 `FlexCarousel`。

    Args:
        warnings (List[Dict[str, Any]]): 包含解析和格式化後預警資訊的字典列表。
     
    Returns:
        Optional[Message]: 構建好的 FlexMessage (可能是 FlexBubble 或 FlexCarousel)；如果沒有預警，返回 None。
    """
    if not warnings:
        return None # 如果沒有任何預警，直接返回 None

    bubbles: List[FlexBubble] = []

    # 遍歷所有預警，為每個預警建立一個 FlexBubble
    for warning in warnings:
        """
        使用一個 `for` 迴圈來迭代傳入的 `warnings` 列表。
        - 動態生成：每個迴圈會根據當前預警字典的內容，動態創建一個完整的 `FlexBubble`。
          這種模式使得程式可以處理任意數量的預警，而無需為每個預警類型編寫單獨的程式碼。
        - 數據提取與組裝：在迴圈內部，首先從 `warning` 字典中安全的提取各項資訊。
          然後將這些資訊組裝成不同的 `FlexBox` 區塊（例如標題、時間、地區、說明），再將這些區塊放入一個主 `FlexBox` 中，最終形成一個 `FlexBubble`。
        - 錯誤處理：使用 `.get(key, default_value)` 來提取數據，可以避免在數據結構不完整時引發 `KeyError`，提高程式的健壯性。
        """
        title = warning.get('title', '無資料')
        issue_time = warning.get('issue_time_formatted', '未知時間')
        effective_period = warning.get('effective_period_formatted', '未知時間')
        affected_areas = warning.get('affected_areas_formatted', '無資料')
        description = warning.get('description_formatted', '無詳細說明')

        title_text = FlexText( # 標題 (例如：【陸上強風特報】)
            text=title,
            weight="bold",
            size="xl",
            color="#FF0000", # 預警類型用紅色
            wrap=True,
            align="center" # 標題置中
        )

        time_info_box = FlexBox( # 時間資訊
            layout="vertical",
            spacing="sm",
            contents=[
                make_kv_row_area_hazard("發布時間：", issue_time),
                make_kv_row_area_hazard("有效期間：", effective_period)
            ],
            paddingTop="sm",
            paddingBottom="sm"
        )

        affected_areas_box = FlexBox( # 影響地區資訊
            layout="vertical",
            spacing="none",
            contents=[
                FlexText(text="影響地區：", weight="bold", size="md", color="#4169E1"),
                FlexText(text=affected_areas, wrap=True, color="#333333", size="md", margin="sm")
            ],
            paddingBottom="sm"
        )
        
        content_box = FlexBox( # 內容說明
            layout="vertical",
            spacing="none",
            contents=[
                FlexText(text="說明：", weight="bold", size="md", color="#4169E1"),
                FlexText(text=description, wrap=True, color="#333333", size="md", margin="sm")
            ],
            paddingTop="sm"
        )

        bubble_contents = FlexBox( # 構建單個預警的 Bubble
            layout="vertical",
            spacing="md",
            contents=[
                title_text,
                FlexSeparator(margin="md", color="#EEEEEE"),
                time_info_box,
                FlexSeparator(margin="md", color="#EEEEEE"),
                affected_areas_box,
                FlexSeparator(margin="md", color="#EEEEEE"),
                content_box
            ],
            paddingAll="20px"
        )

        bubbles.append(
            FlexBubble(
                size="giga",
                body=bubble_contents
            )
        )

    # 根據預警數量返回 FlexBubble 或 FlexCarousel
    """
    根據預警的數量來決定最終返回的 Flex Message 類型。
    如果只有一個預警，直接傳送一個單獨的 `FlexBubble`，用戶可以直接看到訊息。
    如果有兩個或以上的預警，將它們放入一個 `FlexCarousel` 中，用戶可以左右滑動來查看所有預警。
    """
    if len(bubbles) == 1:
        return FlexMessage(
            alt_text="全台地區影響預警",
            contents=bubbles[0]
        )
    else:
        return FlexMessage(
            alt_text="全台地區影響預警",
            contents=FlexCarousel(contents=bubbles)
        )