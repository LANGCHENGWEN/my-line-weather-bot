# typhoon/area_hazard_flex_message.py
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from linebot.v3.messaging.models import (
    Message, FlexBox, FlexText, FlexMessage,
    FlexBubble, FlexSeparator, FlexCarousel
)

logger = logging.getLogger(__name__)

# ———— 小工具：快速做兩欄 Key-Value row ————
def make_kv_row_area_hazard(label: str, value: str) -> FlexBox:
    """
    建立一行兩欄的 Key-Value FlexBox，專為地區預警調整樣式。
    value 參數可以是一個字串，也可以是一個字串列表 (代表多行)。
    """
    # 處理 value 可以是單一字串或字串列表
    if isinstance(value, list):
        value_contents = [
            FlexText(
                text=str(value[0]) + " ~" if value[0] is not None else "N/A",
                wrap=True,
                color="#333333",
                size="md",
                flex=1,
                # margin="sm" # 在垂直Box內，由Box的spacing控制，這裡不設定
            ),
            FlexText(
                text=str(value[1]) if value[1] is not None else "N/A", # 第二個元素保持不變
                wrap=True,
                color="#333333",
                size="md",
                flex=1
            )
        ]
        value_element = FlexBox(
            layout="vertical",
            contents=value_contents,
            spacing="none", # 兩行之間無間距
            flex=1
        )
    else:
        value_element = FlexText(
            text=str(value) if value is not None else "N/A",
            wrap=True,
            color="#333333",
            size="md",
            flex=1,
            margin="sm" # 僅在單行時應用，因為這是一個直接的 FlexText 子元素
        )

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
            value_element # 使用根據類型判斷後得到的元素
        ],
        alignItems="flex-start"
    )

def create_area_hazard_flex_message(
    warnings: List[Dict[str, Any]], target_city: Optional[str] = None
) -> Optional[Message]:
    """
    根據解析後的地區影響預警數據，構建一個 Flex Message。
    每個預警創建一個 Flex Bubble，如果有多個則放入 Flex Carousel。

    Args:
        warnings (List[Dict[str, Any]]): 包含解析後預警資訊的字典列表。
        target_city (Optional[str]): 用戶查詢的目標城市，用於標題顯示。

    Returns:
        Optional[Message]: 構建好的 FlexMessage (可能是 FlexBubble 或 FlexCarousel)，
                          如果沒有預警，返回 None。
    """
    if not warnings:
        return None

    bubbles: List[FlexBubble] = []

    for i, warning in enumerate(warnings):
        phenomena = warning.get('phenomena', '未知現象')
        significance = warning.get('significance', '特報')
        description = warning.get('description', '無詳細說明').strip() # 清理換行符
        affected_areas = warning.get('affected_areas', [])
        start_time = warning.get('start_time', '未知')
        end_time = warning.get('end_time', '未知')
        issue_time = warning.get('issue_time', '未知')

        display_description = description

        # 限制描述的長度，避免 Flex Message 過大
        # display_description = description[:150] + "..." if len(description) > 150 else description

        # 標題 (例如: 【陸上強風特報】)
        title_text = FlexText(
            text=f"【{phenomena}{significance}】",
            weight="bold",
            size="xl",
            color="#FF0000", # 預警類型用紅色
            wrap=True,
            align="center" # 標題置中
        )

        # 時間資訊
        time_info_box = FlexBox(
            layout="vertical",
            spacing="sm",
            contents=[
                make_kv_row_area_hazard("發布時間：", issue_time),
                make_kv_row_area_hazard("有效期間：", [start_time, end_time])
            ],
            paddingTop="sm",
            paddingBottom="sm"
        )

        # 影響地區資訊
        affected_areas_text = ", ".join(affected_areas) if affected_areas else "無"
        affected_areas_box = FlexBox(
            layout="vertical",
            spacing="none",
            contents=[
                FlexText(text="影響地區：", weight="bold", size="md", color="#4169E1"),
                FlexText(text=affected_areas_text, wrap=True, color="#333333", size="md", margin="sm")
            ],
            paddingBottom="sm"
        )
        
        # 內容說明
        content_box = FlexBox(
            layout="vertical",
            spacing="none",
            contents=[
                FlexText(text="說明：", weight="bold", size="md", color="#4169E1"),
                FlexText(text=display_description, wrap=True, color="#333333", size="md", margin="sm")
            ],
            paddingTop="sm"
        )

        # 構建單個預警的 Bubble
        bubble_contents = FlexBox(
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
                size="giga", # 可以選擇 "mega" 或 "giga"
                body=bubble_contents
            )
        )

    # 如果只有一個預警，直接返回該 Bubble，否則返回 Carousel
    if len(bubbles) == 1:
        return FlexMessage(
            alt_text=f"{target_city}地區影響預警" if target_city else "全台地區影響預警",
            contents=bubbles[0]
        )
    else:
        return FlexMessage(
            alt_text=f"{target_city}地區影響預警" if target_city else "全台地區影響預警",
            contents=FlexCarousel(contents=bubbles)
        )

"""
# 簡單的測試
if __name__ == "__main__":
    from datetime import datetime # 確保 datetime 被導入

    # 假設你的 config.py 中有這個 URL
    if not 'CWA_AREA_HAZARD_PORTAL_URL' in locals() and not 'CWA_AREA_HAZARD_PORTAL_URL' in globals():
        CWA_AREA_HAZARD_PORTAL_URL = "https://www.cwa.gov.tw/V8/C/P/Warning/Warning_Hazard.html"


    # 模擬解析後的數據
    sample_warnings_multi = [
        {
            'phenomena': '陸上強風',
            'significance': '特報',
            'description': '一、概述：低壓帶影響，21日下午至22日晚上臺南市、高雄市、屏東縣、澎湖縣局部地區有平均風6級以上或陣風8級以上發生的機率(黃色燈號)，請注意。\n\n二、注意(警戒)事項\n黃色燈號：注意！在戶外請小心路樹、不堅固建築或定置物被強風吹落之碎片；戶外工作者請注意安全；加強牢固戶外物品；行車減速慢行，留意大眾運輸延誤訊息。',
            'affected_areas': ['臺南市', '高雄市', '恆春半島', '屏東縣', '澎湖縣'],
            'start_time': '2025-07-21 16:35:00',
            'end_time': '2025-07-22 23:00:00'
        },
        {
            'phenomena': '大雨',
            'significance': '特報',
            'description': '低壓帶影響，易有短延時強降雨，臺東縣、花蓮縣及屏東縣山區已有局部豪雨發生，今（２１）日花蓮、臺東（含綠島、蘭嶼）、金門、南投山區及恆春半島有局部大雨發生的機率，請注意雷擊、強陣風及溪水暴漲，低窪地區請慎防淹水，連日降雨，山區請慎防坍方、落石、土石流及山洪暴發。',
            'affected_areas': ['南投縣山區', '恆春半島', '花蓮縣', '臺東縣', '蘭嶼綠島', '金門縣'],
            'start_time': '2025-07-21 19:19:00',
            'end_time': '2025-07-22 05:00:00'
        },
        {
            'phenomena': '熱浪',
            'significance': '預警',
            'description': '各地天氣炎熱，請注意防曬，多補充水分，避免中暑。',
            'affected_areas': ['全台'],
            'start_time': '2025-07-21 08:00:00',
            'end_time': '2025-07-21 18:00:00'
        }
    ]

    sample_warnings_single = [
        {
            'phenomena': '陸上強風',
            'significance': '特報',
            'description': '一、概述：低壓帶影響，21日下午至22日晚上臺南市、高雄市、屏東縣、澎湖縣局部地區有平均風6級以上或陣風8級以上發生的機率(黃色燈號)，請注意。\n\n二、注意(警戒)事項\n黃色燈號：注意！在戶外請小心路樹、不堅固建築或定置物被強風吹落之碎片；戶外工作者請注意安全；加強牢固戶外物品；行車減速慢行，留意大眾運輸延誤訊息。',
            'affected_areas': ['臺南市', '高雄市', '恆春半島', '屏東縣', '澎湖縣'],
            'start_time': '2025-07-21 16:35:00',
            'end_time': '2025-07-22 23:00:00'
        }
    ]

    print("--- 生成多條預警 Flex Message (單一 Bubble 內含多個區塊) ---")
    flex_message_multi = create_area_hazard_flex_message(sample_warnings_multi, target_city="全台")
    if flex_message_multi:
        # print(flex_message_multi.as_json_dict()) # 打印完整的 JSON 結構
        print("多條預警 Flex Message 已生成。")
    else:
        print("多條預警 Flex Message 未生成。")

    print("\n--- 生成單條預警 Flex Message ---")
    flex_message_single = create_area_hazard_flex_message(sample_warnings_single, target_city="屏東縣")
    if flex_message_single:
        # print(flex_message_single.as_json_dict()) # 打印完整的 JSON 結構
        print("單條預警 Flex Message 已生成。")
    else:
        print("單條預警 Flex Message 未生成。")
    
    no_warnings_message = create_area_hazard_flex_message([])
    if no_warnings_message is None:
        print("\n--- 無預警時返回 None ---")
"""