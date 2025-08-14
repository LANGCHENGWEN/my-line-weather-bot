# solar_terms/solar_terms_flex_builder.py
"""
將二十四節氣的詳細資訊，轉換為美觀且易讀的 LINE Flex Message。
主要作用：
1. 統一介面外觀：提供一個單一的函式 `build_solar_term_flex_message`，確保所有與節氣相關的訊息（無論是定時推播還是用戶手動查詢）都擁有統一的視覺風格。
2. 數據到 UI 的轉換：將包含節氣名稱、日期、描述、習俗、養生和詩詞等數據的 Python 字典，精確的映射到 Flex Message 的不同 UI 組件（如 `FlexBox`、`FlexText`）。
3. 處理缺失數據：對可能缺失的數據，提供預設值或靈活的佈局處理，確保生成的訊息不會因為資料不完整而出現排版錯誤。
"""
import logging
from linebot.v3.messaging.models import (
    FlexBox, FlexText, FlexBubble,
    FlexMessage, FlexSeparator
)

logger = logging.getLogger(__name__)

def build_solar_term_flex_message(solar_term_data: dict) -> FlexMessage | None:
    """
    接收一個包含單一節氣所有詳細資訊的字典，並根據這些資訊動態建構一個 LINE Flex Message。
    將字典中的各個欄位（名稱、日期、習俗等）提取出來，放入預先設計好的 Flex Message 結構中。
    如果輸入的數據為空，會安全的返回 `None`。
    最後會返回一個完整的 `FlexMessage` 物件，供 LINE Bot 服務發送。
    """
    if not solar_term_data:
        return None # 返回 None

    # --- 處理輸入數據，為每個欄位設定預設值 ---
    """
    從傳入的 `solar_term_data` 字典中提取各項資訊。
    - 安全取值：使用 `.get(key, default_value)` 方法，如果字典中缺少某個鍵，函式會返回預設值，而不是引發 `KeyError` 異常。
    """
    term_name = solar_term_data.get("name", "未知節氣")
    date_str = solar_term_data.get("formatted_date", "未知日期")
    description = solar_term_data.get("description", "無相關描述。")
    customs = solar_term_data.get("customs", "無相關習俗。")
    health = solar_term_data.get("health", "無相關養生建議。")
    poetry = solar_term_data.get("poetry", "無相關詩詞。")

    # --- 構建 Flex Message ---
    body_contents = [
        FlexBox( # 標題
            layout="vertical",
            contents=[
                FlexText(text=f"🍃【{term_name}】節氣小知識 🍃", weight="bold", size="xl", align="center", color="#333333"),
                FlexText(text=f"發生時間：{date_str}", size="md", align="center", color="#666666", margin="sm")
            ]
        ),
        FlexSeparator(margin="lg"),
        FlexBox( # 描述
            layout="vertical",
            contents=[
                FlexText(text="📌 節氣介紹", weight="bold", size="md", color="#0066CC"),
                FlexText(text=description, size="sm", wrap=True, margin="sm", color="#444444")
            ],
            margin="lg"
        ),
        FlexBox( # 習俗
            layout="vertical",
            contents=[
                FlexText(text="🏮 傳統習俗", weight="bold", size="md", color="#CC6600"),
                FlexText(text=customs, size="sm", wrap=True, margin="sm", color="#444444")
            ],
            margin="md"
        ),
        FlexBox( # 養生
            layout="vertical",
            contents=[
                FlexText(text="🌿 養生建議", weight="bold", size="md", color="#009966"),
                FlexText(text=health, size="sm", wrap=True, margin="sm", color="#444444")
            ],
            margin="md"
        ),
        FlexBox( # 詩詞
            layout="vertical",
            contents=[
                FlexText(text="📜 相關詩詞", weight="bold", size="md", color="#663399"),
                FlexText(text=poetry, size="sm", wrap=True, margin="sm", color="#444444", style="italic")
            ],
            margin="md"
        ),
        FlexSeparator(margin="lg"), # 底部提示
        FlexText(text="✨ 24節氣是古人智慧的結晶，指引農事和生活 ✨", size="sm", align="center", color="#AAAAAA", margin="md", wrap=True)
    ]

    # --- 組裝成最終可發送的 Flex Message 物件 ---
    """
    1. FlexBubble：單個 Flex Message 的視覺容器，包含整個訊息的內容。
    2. FlexMessage：是 LINE Messaging API 傳送 Flex 內容的最終頂層物件。
       包含兩個關鍵參數：
        - `alt_text` 提供了當用戶的 LINE 版本太舊或無法顯示 Flex Message 時的後備文字。
        - `contents` 包含剛剛建立的 `FlexBubble` 物件。
    """
    bubble = FlexBubble(
        direction="ltr",
        body=FlexBox(
            layout="vertical",
            contents=body_contents,
            padding_all="20px"
        )
    )
    
    logger.info(f"成功建構節氣 Flex Message: {term_name}")
    return FlexMessage(alt_text=f"{term_name} 節氣小知識", contents=bubble)