# settings/create_push_setting_flex_message.py
"""
動態生成 LINE Flex Message，用於管理各種推播功能的設定。
函式 `create_push_setting_flex_message`根據不同的推播功能，傳入 ID、目前設定狀態及名稱，自動生成一個包含「開啟/關閉」按鈕和當前設定狀態顯示的 Flex Message。
"""
from linebot.v3.messaging.models import (
    FlexBox, FlexText, FlexBubble,
    FlexButton, FlexMessage, FlexSeparator, PostbackAction
)

def create_push_setting_flex_message(feature_id: str, is_enabled: bool, feature_name: str) -> FlexMessage:
    """
    根據傳入的推播功能 ID、當前設定狀態和功能名稱，動態創建一個設定介面的 Flex Message 物件。
    根據 `is_enabled` 的布林值來決定狀態文字（已開啟/已關閉），並將這些資訊嵌入到 Flex Message 的不同組件中。
    最後返回一個完整的 `FlexMessage` 物件，可直接用於 LINE Bot 的回覆。

    Args:
        feature_id: 推播功能的唯一 ID，例如 "daily_reminder"。
        is_enabled: 推播功能目前是否開啟 (True) 或關閉 (False)。
        feature_name: 推播功能的名稱，例如 "每日天氣"。
        
    Returns:
        FlexMessage 物件。
    """
    # --- 根據目前狀態設定文字和顏色 ---
    """
    根據 `is_enabled` 參數來動態設定狀態顯示的文字和顏色。
    """
    if is_enabled:
        status_text = "已開啟"
        status_color = "#1DB446"
    else:
        status_text = "已關閉"
        status_color = "#FF0000"

    # --- 建構 Flex Message 元件 ---
    header_box = FlexBox( # 標題 Box
        layout='vertical',
        contents=[
            FlexText(text=f'{feature_name}推播', weight='bold', size='xl', align="center")
        ]
    )
    
    status_box = FlexBox( # 狀態 Box
        layout='horizontal',
        contents=[
            FlexText(text='目前狀態：', size='md', color='#555555', flex=3),
            FlexText(text=status_text, size='md', color=status_color, flex=6)
        ]
    )

    """
    創建兩個按鈕，用於開啟和關閉推播功能：
    1. 使用 PostbackAction：這裡使用 `PostbackAction` 而不是 `MessageAction`。
       因為 PostbackAction 可以在用戶點擊後向後端發送一個隱藏的 `data` 字串，而不會在聊天視窗中顯示。
    2. 嵌入動態參數：`data` 參數被設計為包含動態資訊。
       例如 `action=set_status&feature={feature_id}&status=on`。
       後端可以解析這個字串，精確的知道用戶想要對哪個功能做什麼操作（開啟或關閉）。
    """
    buttons_box = FlexBox( # 按鈕 Box
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
    
    body_box = FlexBox( # 主要內容 Box
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
    
    bubble = FlexBubble( # Bubble 容器
        body=body_box
    )
    
    # --- 包裝成 FlexMessage 物件，並返回 ---
    """
    將前面定義的所有 UI 組件（FlexBubble）包裝成一個最終的 `FlexMessage` 物件。
    `FlexMessage` 是 LINE Messaging API 傳輸 Flex 內容的頂層容器。
    包含兩個關鍵部分：
    1. `alt_text`：當用戶的 LINE 版本太舊或無法顯示 Flex Message 時，會顯示這段替代文字，為了確保用戶體驗的後備方案。
    2. `contents`：實際的 Flex Message 內容。

    這個完整的 `FlexMessage` 物件會被返回，作為回覆訊息發送給用戶。
    """
    flex_message = FlexMessage( # FlexMessage 物件
        alt_text=f'{feature_name}推播設定',
        contents=bubble
    )
    
    return flex_message