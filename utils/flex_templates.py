# utils/flex_templates.py
"""
使用 LINE Flex Message SDK 建構歡迎訊息。
"""
from linebot.v3.messaging.models import FlexBox, FlexText, FlexBubble, FlexMessage

def build_hello_flex() -> FlexMessage:
    # --- 建構 FlexBubble 的內容 ---
    """
    定義 Flex Message 的主要內容。
    - 使用 `FlexBox` 作為容器：`FlexBox` 是 Flex Message 的核心佈局元件，用於組織內部元件的排列方式。
    - 多個 `FlexText` 元件：透過建立多個 `FlexText` 物件，可以控制不同段落的文字樣式（如粗體、字體大小、顏色和邊距），以達到更好的視覺效果和資訊層次感。
    """
    hello_bubble_content = FlexBubble(
        body=FlexBox(
            layout="vertical", # 使用 `layout="vertical"` 來垂直堆疊內容
            spacing="md",
            contents=[
                FlexText(
                    text="哈囉！您好～ 我是暖心天氣語",
                    weight="bold", # 設定文字為粗體
                    size="lg",     # 設定字體大小為大
                    wrap=True      # 確保文字在超出範圍時自動換行
                ),
                FlexText(
                    text="您可以先設定預設城市，然後點擊選單，我會告訴您天氣資訊和穿搭建議喔！",
                    wrap=True,
                    margin="sm", # 設定與上方元件的間距
                    size="md"
                ),
                FlexText(
                    text="🌟 請輸入您想預設的城市名稱，例如「台中市」或「台北市」，讓我幫您設定預設城市吧！",
                    wrap=True,
                    margin="md",
                    size="md",
                    color="#555555"
                )
            ]
        )
    )

    # --- 將建構好的 `FlexBubble` 物件包裹在頂層的 `FlexMessage` 容器中 ---
    return FlexMessage(
        alt_text="歡迎使用暖心天氣語 ～", # 當用戶的設備無法顯示 Flex Message 時（例如，在舊版客戶端或通知中），LINE 會顯示這個替代文字
        contents=hello_bubble_content   # 傳入上面定義的 FlexBubble 物件
    )