# rich_menu_manager/rich_menu_definitions.py
from linebot.v3.messaging import (
    MessageAction, PostbackAction, RichMenuSize,
    RichMenuArea, RichMenuBounds, RichMenuRequest
)
from linebot.v3.messaging.models import URIAction

# 從 config.py 導入所有需要的變數
from config import NCDR_TYPHOON_PATH_URL
    # MAIN_MENU_ALIAS, # 雖然定義時可能用不到，但在設置 alias 時會用到
    # TYPHOON_ZONE_ALIAS, # 同上
    # WEATHER_QUERY_ALIAS, # 同上
    # LIFESTYLE_REMINDERS_ALIAS, # 同上
    # SETTINGS_ALIAS # 同上

# --- 1. 主要功能選單 ---
def get_main_menu_rich_menu() -> RichMenuRequest:
    """
    定義並返回主要功能選單的 RichMenu 物件。
    """
    return RichMenuRequest(
        size=RichMenuSize(width=2500, height=1686),
        selected=True,  # 設定為預設選中
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
    定義並返回天氣查詢子選單的 RichMenu 物件。
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
            # 注意：您的原始 JSON 中這個按鈕的 x, y 座標是 1250, 843，如果圖片有其他內容會重疊
            # 我假設這是第四個按鈕的位置，與上面「未來預報」的右下方對應。
            RichMenuArea(
                bounds=RichMenuBounds(x=1250, y=843, width=1250, height=843),
                action=PostbackAction(label="回上一頁", data="action=return_to_main_menu")
            )
        ]
    )

# --- 3. 颱風專區子選單 ---
def get_typhoon_zone_rich_menu() -> RichMenuRequest:
    """
    定義並返回颱風專區子選單的 RichMenu 物件。
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
                    uri=NCDR_TYPHOON_PATH_URL  # <--- 從 config.py 導入的 URL
                )
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=843, width=1250, height=843),
                action=MessageAction(text="地區影響預警")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=1250, y=843, width=1250, height=843),
                action=PostbackAction(label="回上一頁", data="action=return_to_main_menu")
            )
        ]
    )

# --- 4. 生活提醒子選單 ---
def get_lifestyle_reminders_rich_menu() -> RichMenuRequest:
    """
    定義並返回生活提醒子選單的 RichMenu 物件。
    """
    return RichMenuRequest(
        size=RichMenuSize(width=2500, height=1686),
        selected=False,
        name="生活提醒子選單",
        chat_bar_text="生活提醒子選單",
        areas=[
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=0, width=1250, height=843),
                action=MessageAction(text="穿搭建議")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=1250, y=0, width=1250, height=843),
                action=MessageAction(text="週末天氣")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=843, width=1250, height=843),
                action=MessageAction(text="節氣小知識")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=1250, y=843, width=1250, height=843),
                action=PostbackAction(label="回上一頁", data="action=return_to_main_menu")
            )
        ]
    )

# --- 5. 設定子選單 ---
def get_settings_rich_menu() -> RichMenuRequest:
    """
    定義並返回設定子選單的 RichMenu 物件。
    """
    return RichMenuRequest(
        size=RichMenuSize(width=2500, height=1686),
        selected=False,
        name="設定子選單",
        chat_bar_text="設定子選單",
        areas=[
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=0, width=1250, height=843),
                action=PostbackAction(data="action=toggle_daily_reminder", displayText="每日提醒推播")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=1250, y=0, width=1250, height=843),
                action=PostbackAction(data="action=toggle_typhoon_notification", displayText="颱風通知推播")
            ),
            # 注意：原始 JSON 中這裡有兩個按鈕重疊或座標有問題 (x=0, y=843, width=833, height=843) 和 (x=833, y=843, width=834, height=843)
            # 並且還有一個 x=0, y=1686 的按鈕，這超出了 2500x1686 的 height 範圍。
            # 我將按照常見的 2x2 或 2x3 佈局調整，並假設您可能想要均勻分佈。
            # 由於原始設定選單有 6 個按鈕，我會嘗試將其分為 3 行 2 列。
            # 這樣每個按鈕高度大約是 1686 / 3 = 562
            # 第一個 x=0, y=1686 的按鈕，其 y 值超出了 height=1686 的範圍。
            # 我將其調整到第三行。

            # 調整後的坐標（假設為3行佈局）
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=843, width=1250, height=421), # 位於第三行上半部分
                action=PostbackAction(data="action=toggle_weekend_weather", label="週末天氣推播")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=1250, y=843, width=1250, height=421), # 位於第三行下半部分，與上一行相對
                action=PostbackAction(data="action=toggle_solar_terms", label="節氣小知識推播")
            ),
            RichMenuArea(
                # 這個按鈕的原始 y 座標 1686 超出範圍，我會把它放在最底層左邊
                bounds=RichMenuBounds(x=0, y=1264, width=1250, height=422), # 調整到最下面一行
                action=PostbackAction(data="action=change_default_city", label="切換預設城市")
            ),
            # 原始JSON中的 "回上一頁" 按鈕座標為 x=1667, y=843, width=833, height=843，這個與 "週末天氣推播" 和 "節氣小知識推播" 有重疊，且寬度不均勻。
            # 我將其調整為位於最底層右邊。
            RichMenuArea(
                bounds=RichMenuBounds(x=1250, y=1264, width=1250, height=422), # 調整到最下面一行右邊
                action=PostbackAction(label="回上一頁", data="action=return_to_main_menu")
            )
        ]
    )