# typhoon/typhoon_flex_message.py
"""
將結構化的颱風數據，轉換為符合 LINE Flex Message 格式的 JSON 物件。
負責所有與 UI 呈現相關的邏輯，將純粹的數據變成使用者在 LINE 訊息中看到的精美卡片。
主要職責：
1. Flex Message 結構建構：根據預先定義好的版面配置（layout），將颱風的各項資訊（如中心位置、風速、預報路徑等）放入不同的 FlexBox 和 FlexText 元件中。
2. 數據顯示與格式化：從傳入的解析後數據中提取值，並進行適當的格式化，例如加上單位（公尺/秒、公里）或添加標籤（中心位置、最大風速）。
3. 錯誤處理與防護：如果傳入的數據無效，會生成一個簡潔的錯誤訊息 Flex Message，而不是讓程式崩潰。
4. 模組化設計：使用輔助函式（如 `make_kv_row` 和 `_get_forecast_section`）來減少重複程式碼，使主要函式 `create_typhoon_flex_message` 保持簡潔且易於閱讀。
"""
import logging
from typing import Any, Dict, Optional
from linebot.v3.messaging.models import (
    FlexBox, FlexText, FlexBubble, FlexButton,
    FlexMessage, FlexSeparator, URIAction
)

from config import CWA_TYPHOON_PORTAL_URL

logger = logging.getLogger(__name__)

# --- 小工具：用於創建一個包含「標籤（label）」和「值（Value）」的水平佈局 FlexBox ---
# 因為樣式跟天氣資訊不一樣，所以這個函式不用通用的 make_kv_row
def make_kv_row(label: str, value: str) -> FlexBox:
    """
    將一個標籤（label）和對應的值（value）組合成一行，並套用預定的顏色和字體大小，以便在颱風資訊卡片中重複使用。
     
    Args:
        label (str): 資訊的標籤，例如 "中心位置"。
        value (str): 資訊的具體內容，預期是一個已格式化好的字串。
     
    Returns:
        FlexBox: 包含標籤和值的 FlexBox 物件。
    """
    return FlexBox(
        layout="baseline",
        spacing="none",
        contents=[
            FlexText(
                text=str(label),
                color="#4169E1",
                size="md",
                flex=0
            ),
            FlexText(
                text=str(value) if value is not None else "無資料",
                wrap=True, # 確保文字在超出範圍時自動換行
                color="#8A2BE2",
                size="md",
                flex=1,
                margin="none"
            )
        ]
    )

# --- 生成颱風資訊 Flex Message 的主要入口 ---
def create_typhoon_flex_message(parsed_typhoon_data: Dict[str, Any]) -> FlexMessage:
    """
    接受一個已經由 `TyphoonParser` 解析和整理過的字典，並基於這個字典的內容動態生成一個完整的 Flex Message 物件，
    包括颱風的現況、未來預報以及一個指向中央氣象署網站的按鈕。
    
    執行流程：
    1. 檢查傳入的數據是否有效，若無效則返回一個錯誤訊息卡片。
    2. 從數據中提取現況和預報資訊。
    3. 組合即時現況的各個 Key-Value 欄位。
    4. 處理特殊格式的暴風半徑資訊。
    5. 使用輔助函式 `_get_forecast_section` 建立未來預報區塊。
    6. 將所有區塊組合成一個完整的 `FlexBubble`。
    7. 添加底部按鈕和替代文字（alt_text），最後返回一個完整的 `FlexMessage` 物件。
    """
    # 1. 檢查數據有效性
    if not parsed_typhoon_data:
        logger.warning("無解析後的颱風數據，無法建立 Flex Message。")
        return FlexMessage( # 返回一個簡潔的錯誤訊息 FlexMessage
            alt_text="颱風資訊載入失敗",
            contents=FlexBubble(
                body=FlexBox(
                    layout="vertical",
                    contents=[
                        FlexText(text="目前無法取得颱風資訊，請稍候再試。", wrap=True, size="md")
                    ]
                )
            )
        )
    
    # 2. 從數據中提取現況和預報資訊
    current_status = parsed_typhoon_data.get('currentStatus', {})
    forecast_24hr = parsed_typhoon_data.get('forecast_24hr', None)
    forecast_48hr = parsed_typhoon_data.get('forecast_48hr', None)
    forecast_72hr = parsed_typhoon_data.get('forecast_72hr', None)

    # 3. 組合即時現況的內容
    realtime_contents = [
        make_kv_row("．中心位置：", f"北緯 {current_status.get('latitude')} 度，東經 {current_status.get('longitude')} 度"),
        make_kv_row("．最大風速：", f"{current_status.get('maxWindSpeed')} 公尺/秒 (陣風 {current_status.get('maxGustSpeed')} 公尺/秒)"),
        make_kv_row("．中心氣壓：", f"{current_status.get('pressure')} hpa"),
        make_kv_row("．移動        ：", f"{current_status.get('movingDirection')}，時速 {current_status.get('movingSpeed')} 公里"),
        make_kv_row(
            "．七級風暴風半徑：", 
            f"{current_status.get('radiusOf7knots')} 公里"
        )
    ]

    # 4. 處理七級風暴風半徑詳細資訊的兩行顯示
    # 格式化為兩行顯示在卡片中
    radius_detail_parts = current_status.get('radiusOf7knotsDetailFormatted', ["", "", "", ""])
    realtime_contents.extend([
        FlexBox( # 第一行方向與半徑的文字
            layout="horizontal", # 橫向佈局
            contents=[
                FlexText(
                    text="　", # 用來對齊的空格
                    size="md",
                    flex=1
                ),
                FlexText(
                    text=radius_detail_parts[0] if len(radius_detail_parts) > 0 and radius_detail_parts[0] else " ",
                    size="md",
                    wrap=True,
                    flex=8 # 佔據大部分空間
                ),
                FlexBox( # 加入一個 FlexBox 來創建大的間隔，並放置第二個方向與半徑的文字
                    layout="horizontal",
                    contents=[
                        FlexText(text="　", flex=2), # 產生中間的間隔，可以調整 flex 值來控制距離
                        FlexText(
                            text=radius_detail_parts[1] if len(radius_detail_parts) > 1 and radius_detail_parts[1] else " ",
                            size="md",
                            wrap=True,
                            flex=8 # 佔據大部分空間
                        )
                    ],
                    flex=8
                )
            ],
            margin="none",
            spacing="none"
        ),
        FlexBox( # 第二行方向與半徑的文字
            layout="horizontal",
            contents=[
                FlexText(
                    text="　", # 同樣的對齊空格
                    size="md",
                    flex=1
                ),
                FlexText(
                    text=radius_detail_parts[2] if len(radius_detail_parts) > 2 and radius_detail_parts[2] else " ",
                    size="md",
                    wrap=True,
                    flex=8
                ),
                FlexBox( # 同樣加入一個 FlexBox 來創建大的間隔，並放置第二個方向與半徑的文字
                    layout="horizontal",
                    contents=[
                        FlexText(text="　", flex=2), # 產生中間的間隔
                        FlexText(
                            text=radius_detail_parts[3] if len(radius_detail_parts) > 3 and radius_detail_parts[3] else " ",
                            size="md",
                            wrap=True,
                            flex=8
                        )
                    ],
                    flex=8
                )
            ],
            margin="none",
            spacing="none"
        )
    ])

    # 5. 未來趨勢預報的輔助函式 (減少重複程式碼)
    def _get_forecast_section(label: str, forecast_data: Optional[Dict[str, Any]]) -> FlexBox:
        """
        生成一個完整的未來預報區塊。
        - 程式碼重用：24小時、48小時和72小時的預報區塊具有相似的結構，將它們的生成邏輯封裝在一個函式中，可以避免重複寫三次幾乎相同的程式碼，讓主函式更短、更乾淨。
        - 錯誤處理：函式內部會檢查 `forecast_data` 是否為 `None`；如果沒有預報數據，返回一個包含「無資料」字樣的簡潔區塊，確保 UI 顯示的完整性，而不是留白或崩潰。
        """
        if not forecast_data:
            return FlexBox(
                layout="vertical",
                spacing="xs",
                contents=[
                    FlexText(
                        text=f"{label} (無資料)",
                        weight="bold",
                        size="md",
                        margin="sm"
                    )
                ]
            )
        
        # 獲取七級風暴風半徑的數據
        radius_7knots_display = f"{forecast_data.get('radiusOf7knots')} 公里" \
                                if forecast_data.get('radiusOf7knots') and \
                                   forecast_data.get('radiusOf7knots').upper() != '無資料' \
                                else "無資料"
        
        return FlexBox(
            layout="vertical",
            spacing="xs",
            contents=[
                FlexText(
                    text=f"{label} ({forecast_data.get('forecastTime')})",
                    weight="bold",
                    size="md",
                    margin="sm"
                ),
                FlexText(
                    text=f"　位置：北緯 {forecast_data.get('latitude')} 度，東經 {forecast_data.get('longitude')} 度",
                    size="sm",
                    wrap=True
                ),
                FlexText(
                    text=f"　最大風速：預估 {forecast_data.get('maxWindSpeed')} 公尺/秒 (陣風 {forecast_data.get('maxGustSpeed')} 公尺/秒)",
                    size="sm",
                    wrap=True
                ),
                FlexText(
                    text=f"　中心氣壓：預估 {forecast_data.get('pressure')} hpa",
                    size="sm",
                    wrap=True
                ),
                FlexText(
                    text=f"　七級風暴風半徑：{radius_7knots_display}，70% 機率半徑：{forecast_data.get('radiusOf70PercentProbability')}",
                    size="sm",
                    wrap=True
                )
            ]
        )
    
    # 6. 組裝完整的 Flex Message
    """
    將所有獨立的 UI 區塊（標題、現況、預報、按鈕）組合在一起，形成一個完整的 `FlexBubble`。
    - 分層組合：遵循 LINE Flex Message 的標準層次結構：`FlexMessage` 包含一個 `FlexBubble`，`FlexBubble` 則由 `header`、`body` 和 `footer` 組成。
    - UI 結構化：使用 `FlexSeparator` 來創建視覺上的分隔線，使得不同區塊（如現況和預報）之間界限分明，提高訊息的可讀性。
    """
    bubble_content = FlexBubble(
        size="giga",
        body=FlexBox(
            layout="vertical",
            contents=[
                FlexText(
                    text=f"🌀 颱風 {current_status.get('typhoonName')} ({current_status.get('typhoonEngName')}) 現況",
                    weight="bold",
                    size="xl",
                    wrap=True,
                    color="#1A64D3"
                ),
                FlexText(
                    text=f"觀測時間：{current_status.get('dataTime')}",
                    size="sm",
                    align="center",
                    color="#888888",
                    margin="sm"
                ),
                FlexSeparator(margin="md"),
                FlexBox(
                    layout="vertical",
                    margin="md",
                    spacing="sm",
                    contents=[
                        FlexText(
                            text="即時現況",
                            weight="bold",
                            size="md",
                            color="#00B900",
                            margin="none"
                        ),
                        FlexBox(
                            layout="vertical",
                            contents=realtime_contents
                        )
                    ]
                ),
                FlexSeparator(margin="md"),
                FlexBox(
                    layout="vertical",
                    margin="md",
                    spacing="sm",
                    contents=[
                        FlexText(
                            text="未來趨勢預報",
                            weight="bold",
                            size="md",
                            color="#FFA500"
                        ),
                        _get_forecast_section("🔹 24 小時後", forecast_24hr),
                        _get_forecast_section("🔹 48 小時後", forecast_48hr),
                        _get_forecast_section("🔹 72 小時後", forecast_72hr)
                    ]
                )
            ]
        ),
        footer=FlexBox(
            layout="vertical",
            spacing="sm",
            contents=[
                FlexButton(
                    style="link",
                    height="sm",
                    action=URIAction(
                        label="查看更多 (中央氣象署)",
                        uri=CWA_TYPHOON_PORTAL_URL
                    )
                )
            ],
            flex=0
        )
    )

    # 7. 返回完整的 FlexMessage 物件
    return FlexMessage(
        alt_text=f"颱風 {current_status.get('typhoonName', '未知')} 警報資訊",
        contents=bubble_content
    )