# typhoon_flex_message.py
import logging
from typing import Any, Dict, List, Optional
from linebot.v3.messaging.models import (
    FlexBox, FlexText, FlexBubble, FlexButton, FlexMessage, FlexSeparator, URIAction
)

from config import CWA_TYPHOON_PORTAL_URL

logger = logging.getLogger(__name__)

# ———— 小工具：快速做兩欄 Key‑Value row ————
# 因為樣式跟天氣資訊不一樣，所以這個函式不用通用的 make_kv_row
def make_kv_row(label: str, value: str) -> FlexBox:
    """
    建立一行兩欄的 Key-Value FlexBox。
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
                text=str(value) if value is not None else "N/A",
                wrap=True,
                color="#8A2BE2",
                size="md",
                flex=1,
                margin="none"
            )
        ]
    )

def create_typhoon_flex_message(parsed_typhoon_data: Dict[str, Any]) -> FlexMessage:
    """
    生成颱風資訊的 Flex Message。
    接受從 TyphoonParser 解析後的颱風數據。
    """
    if not parsed_typhoon_data:
        logger.warning("無解析後的颱風數據，無法建立 Flex Message。")
        # 返回一個簡潔的錯誤訊息 FlexMessage
        return FlexMessage(
            alt_text="颱風資訊載入失敗",
            contents=FlexBubble(
                body=FlexBox(
                    layout="vertical",
                    contents=[
                        FlexText(text="目前無法取得颱風資訊，請稍後再試。", wrap=True, size="md")
                    ]
                )
            )
        )
    
    current_status = parsed_typhoon_data.get('currentStatus', {})
    # forecasts = parsed_typhoon_data.get('forecasts', [])

    # 直接從 parsed_typhoon_data 中取得已篩選好的預報點
    forecast_24hr = parsed_typhoon_data.get('forecast_24hr', None)
    forecast_48hr = parsed_typhoon_data.get('forecast_48hr', None)
    forecast_72hr = parsed_typhoon_data.get('forecast_72hr', None)

    # 即時現況的內容
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

    # 處理七級風暴風半徑詳細資訊的兩行顯示
    radius_detail_parts = current_status.get('radiusOf7knotsDetailFormatted', ["", "", "", ""])
    realtime_contents.extend([
        FlexBox(
            layout="horizontal", # 橫向佈局
            contents=[
                FlexText(
                    text="　", # 用來對齊的空格，佔據與 "．" 相同或類似的空間
                    size="md",
                    flex=1 # 讓它佔據一小部分空間來推動後面的文字
                ),
                FlexText(
                    text=radius_detail_parts[0] if len(radius_detail_parts) > 0 and radius_detail_parts[0] else " ",
                    size="md",
                    wrap=True,
                    flex=8 # 佔據大部分空間
                ),
                # 加入一個 FlexBox 來創建大的間隔，並放置第二個方向的文字
                FlexBox(
                    layout="horizontal",
                    contents=[
                        FlexText(text="　", flex=2), # 這裡用來產生中間的間隔，可以調整 flex 值來控制距離
                        FlexText(
                            text=radius_detail_parts[1] if len(radius_detail_parts) > 1 and radius_detail_parts[1] else " ",
                            size="md",
                            wrap=True,
                            flex=8 # 佔據大部分空間
                        )
                    ],
                    flex=8 # 這個 FlexBox 佔據剩餘大部分空間
                )
            ],
            margin="none",
            spacing="none"
        ),
        FlexBox(
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
                # 同樣的間隔處理
                FlexBox(
                    layout="horizontal",
                    contents=[
                        FlexText(text="　", flex=2), # 這裡用來產生中間的間隔
                        FlexText(
                            text=radius_detail_parts[3] if len(radius_detail_parts) > 3 and radius_detail_parts[3] else " ",
                            size="md",
                            wrap=True,
                            flex=8
                        )
                    ],
                    flex=8 # 這個 FlexBox 佔據剩餘大部分空間
                )
            ],
            margin="none", # 避免額外邊距
            spacing="none"
        )
    ])

    # 未來趨勢預報的函式 (減少重複程式碼)
    def _get_forecast_section(label: str, forecast_data: Optional[Dict[str, Any]]) -> FlexBox:
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
                                   forecast_data.get('radiusOf7knots').upper() != 'N/A' \
                                else "N/A"
        
        return FlexBox(
            layout="vertical",
            spacing="xs",
            contents=[
                FlexText(
                    text=f"{label} ({forecast_data.get('forecastTime', 'N/A')})",
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
                    text=f"觀測時間：{current_status.get('dataTime', 'N/A')}",
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

    # 返回完整的 FlexMessage 物件，包含 alt_text 和 contents
    return FlexMessage(
        alt_text=f"颱風 {current_status.get('typhoonName', '未知')} 警報資訊",
        contents=bubble_content
    )

# 範例使用 (如果需要測試，可以取消下方註解)
# if __name__ == "__main__":
#     flex_message = create_typhoon_flex_message()
#     # 通常會在這裡將 flex_message 發送出去，例如：
#     # line_bot_api.reply_message(event.reply_token, flex_message)
#     # 為了方便查看生成的 JSON，我們可以這樣做：
#     import json
#     print(json.dumps(flex_message.contents.as_json_dict(), ensure_ascii=False, indent=2))