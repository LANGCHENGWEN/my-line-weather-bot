# rich_menu_manager/rich_menu_builder.py
import json
import logging
from linebot.v3.messaging import (
    MessageAction, PostbackAction, RichMenuArea,
    RichMenuSize, RichMenuRequest, RichMenuBounds
)

logger = logging.getLogger(__name__)

def build_rich_menu_request_from_json(json_path: str) -> RichMenuRequest | None:
    """
    從 JSON 檔案讀取數據，構建並返回 RichMenuRequest 物件。
    支持 MessageAction 和 PostbackAction。
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            rich_menu_data = json.load(f)
        
        areas = []
        for area in rich_menu_data.get('areas', []):
            action_type = area.get('action', {}).get('type')
            action = None
            
            if action_type == "message":
                action = MessageAction(
                    label=area['action'].get('label'),
                    text=area['action'].get('text')
                )
            elif action_type == "postback":
                action = PostbackAction(
                    label=area['action'].get('label'),
                    data=area['action'].get('data'),
                    display_text=area['action'].get('displayText')
                )
            else:
                logger.warning(f"未知或未處理的 Rich Menu Action Type: '{action_type}' 在檔案: {json_path}")
                continue

            areas.append(
                RichMenuArea(
                    bounds=RichMenuBounds(
                        x=area['bounds']['x'],
                        y=area['bounds']['y'],
                        width=area['bounds']['width'],
                        height=area['bounds']['height']
                    ),
                    action=action
                )
            )
        
        # 確保 size 是一個 RichMenuSize 物件
        size_data = rich_menu_data.get('size', {'width': 2500, 'height': 1686}) # 提供預設值以防萬一
        size_object = RichMenuSize(width=size_data['width'], height=size_data['height'])

        return RichMenuRequest(
            size=size_object,
            selected=rich_menu_data.get('selected', False),
            name=rich_menu_data.get('name', 'Unnamed Rich Menu'),
            chat_bar_text=rich_menu_data.get('chatBarText', 'Menu'),
            mode=rich_menu_data.get('mode', 'chat'),
            visibility=rich_menu_data.get('visibility', 'always'),
            areas=areas
        )
    except Exception as e:
        logger.error(f"從 JSON 檔案 {json_path} 構建 RichMenuRequest 失敗: {e}", exc_info=True)
        return None