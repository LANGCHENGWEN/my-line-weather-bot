# welcome_flex.py
# 目前未使用
import logging

# 從 linebot.v3.messaging.models 導入 Flex Message 所需的類
from linebot.v3.messaging.models import (
    FlexMessage, FlexBubble, FlexBox,
    FlexText, FlexSeparator, FlexButton, PostbackAction
)

logger = logging.getLogger(__name__)

def create_welcome_flex_message(default_county: str) -> FlexMessage:
    """
    建立一個 Flex Message，用於歡迎使用者並提示輸入鄉鎮市區，
    或選擇查詢其他縣市+鄉鎮市區。

    Args:
        default_county (str): 預設的縣市名稱（例如："臺中市"）。

    Returns:
        FlexMessage: 歡迎 Flex Message 物件。
    """
    logger.info(f"正在創建歡迎 Flex Message，預設城市: {default_county}")

    flex_contents = FlexBubble(
        body=FlexBox(
            layout="vertical",
            contents=[
                FlexText(
                    text=f"您目前的預設城市是 {default_county}。",
                    weight="bold",
                    size="md",
                    wrap=True
                ),
                FlexText(
                    text="請輸入要查詢的鄉鎮市區名稱：",
                    margin="md",
                    size="md",
                    wrap=True
                ),
                FlexText(
                    text="例如：北區",
                    size="sm",
                    color="#aaaaaa",
                    margin="sm"
                ),
                FlexSeparator(
                    margin="lg"
                ),
                FlexButton(
                    action=PostbackAction(
                        label="查詢其他縣市+鄉鎮市區",
                        data="action=set_full_location_input",
                        displayText="請直接輸入縣市+鄉鎮市區，例如：台北市信義區"
                    ),
                    style="primary",
                    color="#1DB446",
                    height="sm",
                    margin="md"
                )
            ]
        )
    )

    return FlexMessage(
        alt_text="天氣預報：請輸入鄉鎮市區",
        contents=flex_contents
    )

logger.info("welcome_flex.py 模組已載入。")