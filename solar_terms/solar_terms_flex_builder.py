# solar_terms/solar_terms_flex_builder.py
import logging
from linebot.v3.messaging.models import (
    FlexBox, FlexText, FlexBubble,
    FlexMessage, FlexSeparator # SpacerComponent
)

logger = logging.getLogger(__name__)

def build_solar_term_flex_message(solar_term_data: dict) -> FlexMessage | None:
    """
    建構節氣小知識的 Flex Message。
    """
    if not solar_term_data:
        return None

    term_name = solar_term_data.get("name", "未知節氣")
    # term_date = solar_term_data.get("date") # 現在會是 datetime 物件
    date_str = solar_term_data.get("formatted_date", "未知日期")
    description = solar_term_data.get("description", "無相關描述。")
    customs = solar_term_data.get("customs", "無相關習俗。")
    health = solar_term_data.get("health", "無相關養生建議。")
    poetry = solar_term_data.get("poetry", "無相關詩詞。")

    # 注意這裡的日期格式化，包含時間
    # date_str = term_date.strftime("%Y年%m月%d日 %H:%M") if term_date else "未知日期"

    body_contents = [
        # 標題
        FlexBox(
            layout="vertical",
            contents=[
                FlexText(text=f"🍃【{term_name}】節氣小知識 🍃", weight="bold", size="xl", align="center", color="#333333"),
                # 現在可以顯示精確的日期和時間
                FlexText(text=f"發生時間：{date_str}", size="md", align="center", color="#666666", margin="sm"),
                # SpacerComponent(size="md")
            ]
        ),
        FlexSeparator(margin="lg"),
        # 描述
        FlexBox(
            layout="vertical",
            contents=[
                FlexText(text="📌 節氣介紹", weight="bold", size="md", color="#0066CC"),
                FlexText(text=description, size="sm", wrap=True, margin="sm", color="#444444"),
                # SpacerComponent(size="md")
            ],
            margin="lg"
        ),
        # 習俗
        FlexBox(
            layout="vertical",
            contents=[
                FlexText(text="🏮 傳統習俗", weight="bold", size="md", color="#CC6600"),
                FlexText(text=customs, size="sm", wrap=True, margin="sm", color="#444444"),
                # SpacerComponent(size="md")
            ],
            margin="md"
        ),
        # 養生
        FlexBox(
            layout="vertical",
            contents=[
                FlexText(text="🌿 養生建議", weight="bold", size="md", color="#009966"),
                FlexText(text=health, size="sm", wrap=True, margin="sm", color="#444444"),
                # SpacerComponent(size="md")
            ],
            margin="md"
        ),
        # 詩詞 (如果存在)
        *([] if poetry == "無相關詩詞。" else [
            FlexBox(
                layout="vertical",
                contents=[
                    FlexText(text="📜 相關詩詞", weight="bold", size="md", color="#663399"),
                    FlexText(text=poetry, size="sm", wrap=True, margin="sm", color="#444444", style="italic"),
                    # SpacerComponent(size="md")
                ],
                margin="md"
            )
        ]),
        # 底部提示
        FlexSeparator(margin="lg"),
        FlexText(text="✨ 24節氣是古人智慧的結晶，指引農事和生活 ✨", size="sm", align="center", color="#AAAAAA", margin="md", wrap=True)
    ]

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