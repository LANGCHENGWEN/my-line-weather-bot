# settings/create_push_setting_flex_message.py
from linebot.v3.messaging.models import (
    FlexBox, FlexText, FlexBubble,
    FlexButton, FlexMessage, FlexSeparator, PostbackAction
)

def create_push_setting_flex_message(feature_id: str, is_enabled: bool, feature_name: str) -> FlexMessage:
    """
    動態生成推播設定的 Flex Message。
    
    Args:
        feature_id: 推播功能的唯一 ID，例如 "daily_reminder"。
        is_enabled: 推播功能目前是否開啟 (True) 或關閉 (False)。
        feature_name: 推播功能的名稱，例如 "每日提醒"。
        
    Returns:
        FlexMessage 物件。
    """
    # 2. 根據目前狀態設定文字和顏色
    if is_enabled:
        status_text = "已開啟"
        status_color = "#1DB446"
    else:
        status_text = "已關閉"
        status_color = "#FF0000"

    # 3. 建構 Flex Message 元件
    
    # 標題 Box
    header_box = FlexBox(
        layout='vertical',
        contents=[
            FlexText(text=f'{feature_name}推播', weight='bold', size='xl', align="center")
        ]
    )
    
    # 狀態 Box
    status_box = FlexBox(
        layout='horizontal',
        contents=[
            FlexText(text='目前狀態：', size='md', color='#555555', flex=3),
            FlexText(text=status_text, size='md', color=status_color, flex=6) # align='start'
        ]
    )

    # 按鈕 Box
    buttons_box = FlexBox(
        layout='horizontal',
        margin='md',
        contents=[
            FlexButton(
                action=PostbackAction(
                    label='開啟',
                    data=f'action=set_status&feature={feature_id}&status=on'
                ),
                style='primary',
                height='sm',
                flex=1,
                margin='sm'
            ),
            FlexButton(
                action=PostbackAction(
                    label='關閉',
                    data=f'action=set_status&feature={feature_id}&status=off'
                ),
                style='secondary',
                height='sm',
                flex=1,
                margin='sm'
            )
        ]
    )
    
    # 主要內容 Box
    body_box = FlexBox(
        layout='vertical',
        contents=[
            header_box,
            FlexSeparator(margin='lg'),
            FlexBox(
                layout='vertical',
                margin='lg',
                spacing='sm',
                contents=[
                    status_box,
                    buttons_box
                ]
            )
        ]
    )
    
    # Bubble 容器
    bubble = FlexBubble(
        body=body_box
    )
    
    # FlexMessage 物件
    flex_message = FlexMessage(
        alt_text=f'{feature_name}推播設定',
        contents=bubble
    )
    
    return flex_message