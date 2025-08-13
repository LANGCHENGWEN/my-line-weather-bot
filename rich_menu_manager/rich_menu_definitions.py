# rich_menu_manager/rich_menu_definitions.py
"""
作為所有 LINE Rich Menu 結構的「藍圖」定義中心。
每個函式都負責生成一個特定 Rich Menu 的 `RichMenuRequest` 物件。
這些物件精確的描述每個 Rich Menu 的尺寸、名稱、區域 (Area) 和對應的動作 (Action)。
例如：當用戶點擊某個 Rich Menu 的特定區域時，是發送一個文字訊息 (`MessageAction`) 還是一個後端回傳事件 (`PostbackAction`)，或是導向一個外部網址 (`URIAction`)。
將 Rich Menu 的結構定義與實際的部署邏輯（`rich_menu_deployer.py`）分開，可以使程式碼更清晰、易於維護。
當需要修改 Rich Menu 的區域或動作時，只需修改這個檔案中的對應函式，而無需觸動其他部分，提高了開發效率。
"""
from linebot.v3.messaging import (
    MessageAction, PostbackAction, RichMenuSize,
    RichMenuArea, RichMenuBounds, RichMenuRequest
)
from linebot.v3.messaging.models import URIAction

# 導入颱風路徑圖外部網址
from config import NCDR_TYPHOON_PATH_URL

# --- 1. 主要功能母選單 ---
def get_main_menu_rich_menu() -> RichMenuRequest:
    """
    定義並返回主要功能母選單的 RichMenuRequest 物件。
    整個 LINE Bot 的導航中心，將用戶引導至四大主要功能：天氣查詢、颱風專區、生活提醒和設定。
    每個功能區都設定為一個 `PostbackAction`，當用戶點擊時，會向後端發送一個包含特定 `data` 參數的事件，觸發後端來切換到對應的子選單。
    """
    return RichMenuRequest(
        size=RichMenuSize(width=2500, height=1686),
        selected=True, # 設定為預設選單
        name="主要功能選單",
        chat_bar_text="點擊開啟功能選單",
        areas=[
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=0, width=1250, height=843),
                action=PostbackAction(label="天氣查詢", data="action=weather_query")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=1250, y=0, width=1250, height=843),
                action=PostbackAction(label="颱風專區", data="action=typhoon_area")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=843, width=1250, height=843),
                action=PostbackAction(label="生活提醒", data="action=lifestyle_reminders")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=1250, y=843, width=1250, height=843),
                action=PostbackAction(label="設定", data="action=settings")
            )
        ]
    )

# --- 2. 天氣查詢子選單 ---
def get_weather_query_rich_menu() -> RichMenuRequest:
    """
    定義並返回天氣查詢子選單的 RichMenuRequest 物件。
    提供兩個功能按鈕：即時天氣和未來預報。
    這兩個按鈕都使用 `MessageAction`，讓用戶點擊後直接發送對應的關鍵字訊息。
    底部則有一個 `PostbackAction` 按鈕，用於讓用戶回退到主選單。
    """
    return RichMenuRequest(
        size=RichMenuSize(width=2500, height=1686),
        selected=False,
        name="天氣查詢子選單",
        chat_bar_text="天氣查詢子選單",
        areas=[
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=0, width=1250, height=843),
                action=MessageAction(text="即時天氣")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=1250, y=0, width=1250, height=843),
                action=MessageAction(text="未來預報")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=1250, y=843, width=1250, height=843),
                action=PostbackAction(label="回首頁", data="action=return_to_main_menu")
            )
        ]
    )

# --- 3. 颱風專區子選單 ---
def get_typhoon_zone_rich_menu() -> RichMenuRequest:
    """
    定義並返回颱風專區子選單的 RichMenuRequest 物件。
    包含三個主要功能按鈕：
    1. 颱風現況：`MessageAction`，讓用戶發送關鍵字查詢當前颱風資訊。
    2. 颱風路徑圖：`URIAction`，將用戶直接導向颱風路徑圖網頁，避免在 LINE Bot 內部處理複雜的圖片生成和更新，並確保資訊來源的權威性。
    3. 地區影響預警：`MessageAction`，查詢特定地區的影響預報。
    - 回首頁：`PostbackAction`，讓用戶回到主選單。
    """
    return RichMenuRequest(
        size=RichMenuSize(width=2500, height=1686),
        selected=False,
        name="颱風專區子選單",
        chat_bar_text="颱風專區子選單",
        areas=[
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=0, width=1250, height=843),
                action=MessageAction(text="颱風現況")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=1250, y=0, width=1250, height=843),
                action=URIAction(
                    label="颱風路徑圖",
                    uri=NCDR_TYPHOON_PATH_URL
                )
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=843, width=1250, height=843),
                action=MessageAction(text="地區影響預警")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=1250, y=843, width=1250, height=843),
                action=PostbackAction(label="回首頁", data="action=return_to_main_menu")
            )
        ]
    )

# --- 4. 生活提醒子選單 ---
def get_lifestyle_reminders_rich_menu() -> RichMenuRequest:
    """
    定義並返回生活提醒子選單的 RichMenuRequest 物件。
    包含三個生活相關的功能按鈕，都使用 `PostbackAction`：
    1. 穿搭建議：提供根據天氣的穿搭建議。
    2. 週末天氣：查詢週末的詳細天氣預報。
    3. 節氣小知識：提供當天或最近節氣的相關資訊。
    - 回首頁：讓用戶回到主選單。
    每個功能都發送一個獨特的 `data` 參數，讓後端能夠精準的觸發對應的邏輯。
    """
    return RichMenuRequest(
        size=RichMenuSize(width=2500, height=1686),
        selected=False,
        name="生活提醒子選單",
        chat_bar_text="生活提醒子選單",
        areas=[
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=0, width=1250, height=843),
                action=PostbackAction(label="穿搭建議", data="action=outfit_advisor")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=1250, y=0, width=1250, height=843),
                action=PostbackAction(label="週末天氣", data="action=weekend_weather")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=843, width=1250, height=843),
                action=PostbackAction(label="節氣小知識", data="action=solar_term_info")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=1250, y=843, width=1250, height=843),
                action=PostbackAction(label="回首頁", data="action=return_to_main_menu")
            )
        ]
    )

# --- 5. 設定子選單 ---
def get_settings_rich_menu() -> RichMenuRequest:
    """
    定義並返回設定子選單的 RichMenuRequest 物件。
    提供一個界面，讓用戶能夠開啟或關閉各種推播通知，以及更改預設城市。
    每個設定按鈕都使用 `PostbackAction`，推播設定按鈕的 `data` 參數與後端處理邏輯中的 `FEATURE_ID` 緊密對應，這樣後端就可以根據收到的 `data` 參數，精準的切換用戶的推播設定狀態。
    """
    return RichMenuRequest(
        size=RichMenuSize(width=2500, height=1686),
        selected=False,
        name="設定子選單",
        chat_bar_text="設定子選單",
        areas=[
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=0, width=833, height=843),
                action=PostbackAction(label="每日天氣推播", data="action=daily_reminder_push")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=833, y=0, width=834, height=843),
                action=PostbackAction(label="颱風通知推播", data="action=typhoon_notification_push")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=1667, y=0, width=833, height=843),
                action=PostbackAction(label="週末天氣推播", data="action=weekend_weather_push")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=843, width=833, height=843),
                action=PostbackAction(label="節氣小知識推播", data="action=solar_terms_push")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=833, y=843, width=834, height=843),
                action=PostbackAction(label="切換預設城市", data="action=change_default_city")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=1667, y=843, width=833, height=843),
                action=PostbackAction(label="回首頁", data="action=return_to_main_menu")
            )
        ]
    )