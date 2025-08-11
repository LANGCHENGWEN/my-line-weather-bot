# firestore_manager.py
import os
import json
import logging
from typing import Any, List, Dict, Optional
from .major_stations import ALL_TAIWAN_COUNTIES

# 引入 Firebase Admin 函式庫
import firebase_admin
from firebase_admin import firestore, credentials
from google.cloud.firestore_v1.base_document import DocumentSnapshot

logger = logging.getLogger(__name__)

# --- 初始化 Firebase 應用程式 ---
def initialize_firebase():
    """
    初始化 Firebase Admin SDK。
    """
    try:
        # 從環境變數中讀取 JSON 憑證內容
        cred_json = os.environ.get("FIREBASE_ADMIN_SDK")

        # 檢查環境變數是否存在
        if not cred_json:
            raise ValueError("環境變數 'FIREBASE_ADMIN_SDK' 不存在。")
        
        # 將 JSON 字串轉換成字典
        cred_dict = json.loads(cred_json)

        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        logger.info("Firebase Firestore 連線成功。")
    except Exception as e:
        logger.error(f"Firebase 連線失敗: {e}", exc_info=True)
        raise RuntimeError("無法連線到 Firebase Firestore") from e

# 確保在程式啟動時只初始化一次
if not firebase_admin._apps:
    initialize_firebase()

db = firestore.client()
users_ref = db.collection('users')

# --- 核心 Firestore 工具函數 ---
def _upsert_cols(user_id: str, **data: Any) -> None:
    """
    更新或插入用戶資料到 Firestore。
    使用 set(..., merge=True) 可以只更新指定欄位，不影響其他欄位。
    """
    doc_ref = users_ref.document(user_id)
    doc_ref.set(data, merge=True)

def get_all_users() -> List[DocumentSnapshot]:
    """
    獲取所有 Firestore 用戶文件。
    """
    return users_ref.stream()

def get_user_data(user_id: str) -> Optional[Dict[str, Any]]:
    """
    從 Firestore 取得指定用戶的資料。
    """
    doc_ref = users_ref.document(user_id)
    doc = doc_ref.get()
    return doc.to_dict() if doc.exists else None

# --- 業務邏輯函數 (已從 SQLite3 改寫為 Firestore) ---
def get_users_by_city() -> Dict[str, List[str]]:
    """
    獲取一個字典，鍵為城市名稱，值為該城市所有用戶 ID 的列表。
    改為使用 Firestore 的高效查詢，以城市作為篩選條件。

    查詢所有用戶的 default_city。
    """
    city_users = {}

    # 這裡我們需要遍歷所有的城市，然後為每個城市執行一個查詢
    for city in ALL_TAIWAN_COUNTIES:
        # 查詢所有 default_city 欄位等於當前城市的文件
        docs = users_ref.where('default_city', '==', city).stream()

        user_ids = []
        for doc in docs:
            user_ids.append(doc.id)

        if user_ids:
            city_users[city] = user_ids
            
    return city_users

def set_user_state(user_id: str, state: str, data: Dict[str, Any] = None):
    """
    設定指定使用者的狀態，並可儲存相關的額外數據。
    """
    # 獲取現有的 metadata，以便合併新的 data
    current_meta = get_user_metadata(user_id, "all_meta", {})
    
    # 更新或設定 'state_data' 鍵
    current_meta['state_data'] = data if data is not None else {}
    
    _upsert_cols(user_id, state=state, meta_json=current_meta)
    logger.debug(f"已設定使用者狀態: user_id={user_id}, state={state}, data={data}")

def get_user_state(user_id: str) -> Dict[str, Any]:
    """
    取得指定使用者的當前狀態及其相關數據。
    """
    user_data = get_user_data(user_id)
    if user_data:
        state = user_data.get('state', 'idle')
        meta = user_data.get('meta_json', {})
        data_from_meta = meta.get('state_data', {})
        return {"state": state, "data": data_from_meta}
    else:
        return {"state": "idle", "data": {}}

def clear_user_state(user_id: str) -> None:
    """清除指定使用者的狀態和相關數據。"""
    current_meta = get_user_metadata(user_id, "all_meta", {})
    if 'state_data' in current_meta:
        del current_meta['state_data']
    _upsert_cols(user_id, state=None, meta_json=current_meta)

def save_default_city(user_id: str, city_name: str) -> None:
    """儲存指定使用者的預設城市。"""
    _upsert_cols(user_id, default_city=city_name)

def get_default_city(user_id: str) -> Optional[str]:
    user_data = get_user_data(user_id)
    return user_data.get('default_city') if user_data else None

def set_user_metadata(user_id: str, **kwargs: Any) -> None:
    """
    設定指定使用者的任意 metadata。
    """
    current_meta = get_user_metadata(user_id, "all_meta", {})
    current_meta.update(kwargs)
    _upsert_cols(user_id, meta_json=current_meta)

def get_user_metadata(user_id: str, key: str, default: Any = None) -> Any:
    """
    獲取指定使用者的某個 metadata。
    """
    user_data = get_user_data(user_id)
    if not user_data:
        return {} if key == "all_meta" else default
    
    full_meta = user_data.get('meta_json', {})
    if key == "all_meta":
        return full_meta
        
    return full_meta.get(key, default)

def is_valid_city(city_name: str) -> bool:
    """
    驗證給定的城市名稱是否在有效城市列表中。
    """
    return city_name in ALL_TAIWAN_COUNTIES

def get_user_push_settings(user_id: str) -> Dict[str, bool]:
    """
    獲取指定用戶的推播設定。
    在發送推播前，會為每個用戶單獨查詢，確認他們是否開啟了 FEATURE_ID (推播功能名稱)。
    """
    return get_user_metadata(user_id, "push_settings", {})

def update_user_push_setting(user_id: str, feature_id: str, is_enabled: bool):
    """更新指定用戶的單個推播設定。"""
    current_push_settings = get_user_push_settings(user_id)
    current_push_settings[feature_id] = is_enabled
    set_user_metadata(user_id, push_settings=current_push_settings)
    logger.info(f"用戶 {user_id} 的 {feature_id} 推播已設定為: {is_enabled}")

def get_users_with_push_enabled(feature_id: str) -> List[str]:
    """
    獲取所有開啟特定推播功能的用戶 ID。
    Firestore 查詢，尋找 meta_json.push_settings.feature_id 為 true 的用戶。
    """
    enabled_users = []
    # 注意：這需要你在 Firestore 中建立對應的索引。

    # 使用 Firestore 的 .where() 查詢，效率更高
    docs = users_ref.where(f'meta_json.push_settings.{feature_id}', '==', True).stream()
    
    for doc in docs:
        enabled_users.append(doc.id)
            
    return enabled_users

SYSTEM_USER_ID = "system_metadata" 

def get_system_metadata(key: str, default: Any = None) -> Any: # 讀取上次推播的颱風 ID
    """獲取系統級的元數據。"""
    return get_user_metadata(SYSTEM_USER_ID, key, default)

def set_system_metadata(**kwargs: Any) -> None: # 寫入這次推播的颱風 ID
    """設定系統級的元數據。"""
    set_user_metadata(SYSTEM_USER_ID, **kwargs)