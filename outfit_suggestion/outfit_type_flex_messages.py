# outfit_suggestion/outfit_type_flex_messages.py
"""
生成一個 LINE Flex Message，作為穿搭建議功能的主選單。
根據用戶指定的城市動態創建一個包含多個選項的卡片，選項包括「今日穿搭建議」、「即時穿搭建議」和「未來穿搭建議」，以及一個「查詢其他縣市」的按鈕。
將 UI 呈現邏輯與後端處理邏輯分離，提高程式碼的可讀性和可維護性。
"""
from linebot.v3.messaging.models import (
    FlexBox, FlexText, FlexImage, FlexBubble,
    FlexButton, FlexMessage, FlexSeparator, PostbackAction
)

def build_outfit_suggestions_flex(target_query_city: str, default_city_display: str) -> FlexMessage:
    """
    生成一個單一 Flex Message 卡片選單，包含今日、即時、未來穿搭建議選項。
    將用戶當前查詢的城市名稱 (target_query_city) 嵌入到每個按鈕的 Postback data 中，這樣在用戶點擊按鈕後，後端處理器就能準確知道要查詢哪個城市的資訊。
    target_query_city：用戶當前查詢的城市名稱 (用於 Postback data)。
    default_city_display：用戶預設城市（用於顯示，如果沒有則為「未設定」）。
    """
    # --- 輔助函式：用於生成穿搭建議按鈕 ---
    def _outfit_button(label: str, data_type: str) -> FlexButton:
        """
        將重複的按鈕創建邏輯抽象化，減少了重複程式碼。
        通過傳入不同的 `label` 和 `data_type`，可以快速且一致的生成多個按鈕。
        每個按鈕都包含了特定的 Postback data，方便後續的事件處理器解析。
        """
        return FlexButton(
            action=PostbackAction(
                label=label,
                data=f"action=outfit_query&type={data_type}&city={target_query_city}"
            ),
            style="primary",
            color="#00B900",
            height="sm",
            margin="md"
        )

    # --- 輔助函式：用於生成「查詢其他縣市」按鈕 ---
    def _other_location_button() -> FlexButton:
        """
        將這類特殊按鈕的創建邏輯分離，使樣式和行為與主要功能按鈕區隔開來。
        這種設計讓按鈕的職責更清晰，同時使用了不同的顏色和間距，以提供更好的視覺引導。
        """
        return FlexButton(
            action=PostbackAction(
                type="postback",
                label="查詢其他縣市",
                data="action=outfit_other_city"
            ),
            style="secondary",
            color="#AAAAAA", # 灰色，與主要按鈕區隔
            height="sm",
            margin="lg" # 增加上方間距，與穿搭建議按鈕區隔
        )
    
    # --- 組裝整個 Flex Message 結構 ---
    """
    根據 LINE Flex Message 的 JSON 格式所建立的物件結構。
    `FlexBubble` 作為最外層的容器，包含了 `hero`（頂部橫幅圖片）和 `body`（內容區）兩個主要部分。
    
    `hero` 區塊放置一張橫幅圖片，用來增加訊息的視覺吸引力。
    `body` 區塊則是一個 `FlexBox`，按照垂直方向依次放置了標題、副標題、說明文字、分隔線和前面定義好的按鈕。
    
    通過 `FlexMessage` 物件將 `FlexBubble` 包裝起來，可以直接發送。
    """
    bubble = FlexBubble(
        direction="ltr",
        hero=FlexBox(
            layout="vertical",
            contents=[
                FlexImage(
                    url="https://i.postimg.cc/v8fkC8qK/Outfit-suggestions.jpg",
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
                    text="👗 穿搭建議 👔",
                    weight="bold",
                    size="xl",
                    align="center",
                    margin="md"
                ),
                FlexText(
                    text=f"您的預設城市：{default_city_display}", # 顯示用戶預設城市
                    size="sm",
                    color="#666666",
                    align="center",
                    margin="sm",
                    wrap=True # 確保文字在超出範圍時自動換行
                ),
                FlexText(
                    text="請選擇您想查詢的穿搭時段：",
                    size="sm",
                    color="#999999",
                    align="center",
                    margin="md"
                ),
                FlexSeparator(margin="lg"),
                _outfit_button("☀️ 今日穿搭建議", "today"),
                _outfit_button("⏰ 即時穿搭建議", "current"),
                _outfit_button("📅 未來穿搭建議 (1-7天)", "forecast"),
                _other_location_button() # 查詢其他縣市按鈕
            ]
        )
    )

    return FlexMessage(
        alt_text="穿搭建議選單", # 訊息預覽文字
        contents=bubble
    )