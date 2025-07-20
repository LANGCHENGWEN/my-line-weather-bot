# typhoon_flex_message.py
import re
import logging
from typing import Any, Dict, Optional
from linebot.v3.messaging.models import (
    FlexBox, FlexText, FlexBubble, FlexButton, FlexSeparator, URIAction
)

from .typhoon_constants import DIRECTION_MAP

logger = logging.getLogger(__name__)

# ———— 小工具：快速做兩欄 Key‑Value row ————
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

def format_radius_detail_cht(detail_str: str) -> list[str]:
    """
    將英文縮寫的風暴半徑詳細資訊轉換為中文。
    例如: "(NE170公里, SE180公里)" -> "(東北170公里, 東南180公里)"
    """
    if not detail_str:
        return [] # 返回空列表
    
    # 這裡加入對 DIRECTION_MAP 的檢查，以防萬一它變成 None
    if DIRECTION_MAP is None:
        logger.error("format_radius_detail_cht 中的 DIRECTION_MAP 為 None。這表示存在導入問題。")
        return [detail_str] # 無法轉換，返回包含原始字串的列表
    
    parts = re.split(r',\s*', detail_str.strip('() '))
    
    formatted_parts = []
    
    # 遍歷 DIRECTION_MAP，先替換較長的詞，確保 "NNE" 不會被 "N" 先替換
    try:
        sorted_directions = sorted(
            [k for k in DIRECTION_MAP.keys() if k is not None], 
            key=len, 
            reverse=True
        )
    except TypeError as e:
        logger.error(f"Error sorting DIRECTION_MAP keys: {e}. DIRECTION_MAP: {DIRECTION_MAP}")
        return [detail_str] # 無法轉換，返回包含原始字串的列表

    for part in parts:
        if not part:
            continue
        # 遍歷排序過的方向，嘗試替換
        replaced = False
        for eng_dir in sorted_directions:
            if eng_dir and part.startswith(eng_dir):
                remaining_part = part[len(eng_dir):]
                formatted_parts.append(f"{DIRECTION_MAP[eng_dir]}{remaining_part}")
                replaced = True
                break
        if not replaced: # 如果沒有匹配到任何方向，則保留原樣
            formatted_parts.append(part)

    return formatted_parts # 返回列表

def create_typhoon_flex_message(
    current_status: Dict[str, Any],
    forecast_24hr: Optional[Dict[str, Any]],
    forecast_48hr: Optional[Dict[str, Any]],
    forecast_72hr: Optional[Dict[str, Any]]
) -> FlexBubble:
    """
    生成颱風資訊的 Flex Message。
    接受解析後的颱風數據。
    """
    # 獲取並轉換移動方向
    moving_direction_eng = current_status.get('movingDirection')
    # 這裡也加入對 DIRECTION_MAP 的檢查
    if DIRECTION_MAP is None:
        moving_direction_cht = moving_direction_eng # 無法轉換，使用原始英文
        logger.error("轉換 movingDirection 時 DIRECTION_MAP 為 None。")
    else:
        moving_direction_cht = DIRECTION_MAP.get(moving_direction_eng, moving_direction_eng)

    # 獲取並轉換七級風暴風半徑詳細資訊 (現在會返回列表)
    radius_detail_parts = format_radius_detail_cht(current_status.get('radiusOf7knotsDetail', ''))

    # 即時現況的內容
    realtime_contents = [
        make_kv_row("．中心位置：", f"北緯 {current_status.get('latitude')} 度，東經 {current_status.get('longitude')} 度"),
        make_kv_row("．最大風速：", f"{current_status.get('maxWindSpeed')} 公尺/秒 (陣風 {current_status.get('maxGustSpeed')} 公尺/秒)"),
        make_kv_row("．中心氣壓：", f"{current_status.get('pressure')} hpa"),
        make_kv_row("．移動        ：", f"{moving_direction_cht}，時速 {current_status.get('movingSpeed')} 公里"),
        make_kv_row(
            "．七級風暴風半徑：", 
            f"{current_status.get('radiusOf7knots')} 公里"
        ),
        # 這裡開始處理半徑詳細資訊的兩行顯示
        FlexBox(
            layout="horizontal", # 橫向佈局
            contents=[
                FlexText(
                    text="　", # 用來對齊的空格，佔據與 "．" 相同或類似的空間
                    size="md",
                    flex=1 # 讓它佔據一小部分空間來推動後面的文字
                ),
                FlexText(
                    text=radius_detail_parts[0] if len(radius_detail_parts) > 0 else "",
                    size="md",
                    wrap=True,
                    flex=8 # 佔據大部分空間
                ),
                FlexText(
                    text=radius_detail_parts[1] if len(radius_detail_parts) > 1 else "",
                    size="md",
                    wrap=True,
                    flex=8 # 佔據大部分空間
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
                    text=radius_detail_parts[2] if len(radius_detail_parts) > 2 else "",
                    size="md",
                    wrap=True,
                    flex=8
                ),
                FlexText(
                    text=radius_detail_parts[3] if len(radius_detail_parts) > 3 else "",
                    size="md",
                    wrap=True,
                    flex=8
                )
            ],
            margin="none", # 避免額外邊距
            spacing="none"
        )
    ]

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
        radius_7knots = forecast_data.get('radiusOf7knots')
        # 判斷是否為 N/A 或 None，並格式化顯示
        # 將 'None' (字串) 和 None (Python 物件) 都視為無效數據
        radius_7knots_display = f"{radius_7knots} 公里" if radius_7knots and radius_7knots.upper() != 'N/A' else "N/A"
        
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
    
    return FlexBubble(
        alt_text=f"颱風 {current_status.get('typhoonName', '未知')} 警報資訊",
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
                        uri="https://www.cwa.gov.tw/V8/C/P/Typhoon/TY_NEWS.html"
                    )
                )
            ],
            flex=0
        )
    )

# 範例使用 (如果需要測試，可以取消下方註解)
# if __name__ == "__main__":
#     flex_message = create_typhoon_flex_message()
#     # 通常會在這裡將 flex_message 發送出去，例如：
#     # line_bot_api.reply_message(event.reply_token, flex_message)
#     # 為了方便查看生成的 JSON，我們可以這樣做：
#     import json
#     print(json.dumps(flex_message.contents.as_json_dict(), ensure_ascii=False, indent=2))