# utils/firestore_manager.py
"""
中央化的數據庫管理模組，專門用於處理與 Google Cloud Firestore 的所有交互。
將複雜的數據庫操作（如連線、查詢、更新、讀取）封裝在簡單易用的 Python 函式中，為應用程式的其他部分提供服務。
主要職責：
1. Firebase 初始化與連線管理：使用 Google Application Default Credentials (ADC) 機制安全的初始化 Firebase 應用程式，確保在部署環境中透過服務帳號 (Service Account) 取得權限，並確保連線只在程式啟動時執行一次。
2. 基本 CRUD 操作：提供通用的函式來新增、讀取、更新和刪除用戶資料。
3. 業務邏輯抽象：將與特定業務相關的數據庫操作（如設定用戶狀態、儲存預設城市、管理推播設定）封裝為高層次的函式，使呼叫這些函式的地方不需要知道 Firestore 的內部細節。
4. 系統級數據管理：新增處理系統級元數據的功能，例如儲存上次推播的颱風 ID，這對於自動化任務非常重要。
"""
import logging
from typing import Any, List, Dict, Optional
from .major_stations import ALL_TAIWAN_COUNTIES

# 導入 Firebase Admin 函式庫
import firebase_admin
from firebase_admin import firestore
from firebase_admin.credentials import ApplicationDefault
from google.cloud.firestore_v1.base_document import DocumentSnapshot

logger = logging.getLogger(__name__)

# --- 初始化 Firebase Admin SDK ---
def initialize_firebase():
    """
    建立與 Firebase Firestore 的連線。
    使用 Google Application Default Credentials (ADC) 自動從部署環境 (如 Cloud Run 服務帳號) 取得憑證來初始化 Firebase Admin SDK。
    """
    try:
        # 建立憑證物件時，使用 ApplicationDefault() 來自動取得憑證
        cred = ApplicationDefault()

        # 初始化應用程式
        firebase_admin.initialize_app(cred)
        logger.info("Firebase Firestore 連線成功。")
    except Exception as e:
        # 如果初始化過程中有任何錯誤（例如憑證格式不正確、環境變數不存在），會捕獲異常並記錄
        logger.error(f"Firebase 連線失敗: {e}", exc_info=True)
        # 接著拋出一個自訂的 RuntimeError，讓調用者知道連線失敗，並停止程式執行
        raise RuntimeError("無法連線到 Firebase Firestore") from e

# --- 確保在程式啟動時只初始化一次 ---
"""
`firebase_admin._apps` 是一個內部屬性，用於追蹤已初始化的應用程式。
這段程式碼檢查應用程式是否已經初始化過；如果沒有，就呼叫 `initialize_firebase()` 函式。
防止在應用程式被多次導入或重新載入時，重複初始化 Firebase，避免不必要的錯誤和資源浪費。
"""
if not firebase_admin._apps:
    initialize_firebase()

# 取得 Firestore 客戶端和用戶資料集的引用
db = firestore.client()
users_ref = db.collection('users')

# --- 更新或插入用戶資料到 Firestore ---
def _upsert_cols(user_id: str, **data: Any) -> None:
    """
    這個函式是所有寫入操作的底層核心。
    將任意鍵值對 (`**data`) 安全的寫入或更新到指定的用戶文件中。
    使用 set(..., merge=True) 可以只更新指定欄位，不影響其他欄位。
    """
    doc_ref = users_ref.document(user_id)
    # 確保只更新指定的欄位，而不會覆蓋文件中已存在的其他欄位
    # 例如，如果只傳入 `default_city`，那 `state` 和 `meta_json` 欄位將不受影響
    doc_ref.set(data, merge=True)

# ---獲取所有 Firestore 用戶文件 ---
def get_all_users() -> List[DocumentSnapshot]:
    """
    返回一個迭代器（stream），這比一次性載入所有文件更有效率，特別是當用戶數量非常龐大時。
    """
    return users_ref.stream()

# --- 從 Firestore 取得指定用戶的資料 ---
def get_user_data(user_id: str) -> Optional[Dict[str, Any]]:
    """
    這個函式是所有讀取操作的底層核心。
    根據 `user_id` 取得文件，並轉換為 Python 字典。
    """
    doc_ref = users_ref.document(user_id)
    doc = doc_ref.get() # `.get()` 方法返回一個 DocumentSnapshot 物件
    # `.exists` 屬性可以安全的檢查文件是否存在，避免在文件不存在時訪問其數據而導致錯誤
    # `to_dict()` 將文件內容轉換為字典
    return doc.to_dict() if doc.exists else None

# --- 查詢所有用戶的預設城市 ---
def get_users_by_city() -> Dict[str, List[str]]:
    """
    獲取一個字典，鍵為城市名稱，值為該城市所有用戶 ID 的列表。
    使用 Firestore 的高效查詢，以城市作為篩選條件。
    """
    city_users = {}

    # 遍歷所有的城市，為每個城市執行一次查詢
    for city in ALL_TAIWAN_COUNTIES:
        """
        由於 Firestore 的查詢限制，無法直接一次性查詢多個城市。
        最簡單且安全的方法是遍歷所有城市，為每個城市執行一次 `.where()` 查詢。
        對每個在 `ALL_TAIWAN_COUNTIES` 列表中的城市，向 Firestore 傳送一個查詢請求，找出 `default_city` 欄位與之匹配的所有用戶。
        然後將這些用戶的 ID 收集起來，並存儲在 `city_users` 字典中。
        """
        docs = users_ref.where('default_city', '==', city).stream() # 查詢所有 default_city 欄位等於當前城市的文件

        user_ids = []
        for doc in docs:
            user_ids.append(doc.id)

        if user_ids:
            city_users[city] = user_ids
            
    return city_users

# --- 設定指定用戶的狀態，並儲存相關的額外數據 ---
def set_user_state(user_id: str, state: str, data: Dict[str, Any] = None):
    """
    這個函式用於管理機器人的對話狀態，例如在多步驟對話中追蹤用戶進度。
    """
    # 獲取現有的 metadata，以便合併新的 data
    current_meta = get_user_metadata(user_id, "all_meta", {})
    
    # 將狀態相關數據存儲在 metadata 的 'state_data' 鍵下
    current_meta['state_data'] = data if data is not None else {}
    
    # 呼叫底層的 `_upsert_cols` 函式來更新數據庫
    # `_upsert_cols` 的 `merge=True` 確保只更新 `state` 和 `meta_json` 這兩個欄位，而不會影響用戶文件中的其他資料
    _upsert_cols(user_id, state=state, meta_json=current_meta)
    logger.debug(f"已設定用戶狀態: user_id={user_id}, state={state}, data={data}")

# --- 取得指定用戶的當前狀態及相關數據 ---
def get_user_state(user_id: str) -> Dict[str, Any]:
    """
    這個函式是 `set_user_state` 的反向操作，用於在每次收到用戶訊息時，查詢用戶當前所處的對話狀態。
    """
    user_data = get_user_data(user_id)
    if user_data:
        # 從用戶數據中安全的取得 `state` 和 `meta_json` 欄位，並提供預設值以防止錯誤
        state = user_data.get('state', 'idle')
        meta = user_data.get('meta_json', {})
        data_from_meta = meta.get('state_data', {})
        return {"state": state, "data": data_from_meta}
    else:
        # 如果用戶不存在，返回預設的閒置狀態
        return {"state": "idle", "data": {}}

# --- 清除指定用戶的狀態和相關數據 ---
def clear_user_state(user_id: str) -> None:
    """
    在對話結束時重置用戶狀態。
    """
    current_meta = get_user_metadata(user_id, "all_meta", {})
    if 'state_data' in current_meta:
        del current_meta['state_data'] # 如果存在，則刪除 `state_data` 鍵
    # 將 `state` 欄位設定為 `None` 來清除它
    _upsert_cols(user_id, state=None, meta_json=current_meta)

# --- 儲存指定用戶的預設城市 ---
def save_default_city(user_id: str, city_name: str) -> None:
    _upsert_cols(user_id, default_city=city_name)

# --- 從 Firestore 取得指定用戶的預設城市 ---
def get_default_city(user_id: str) -> Optional[str]:
    user_data = get_user_data(user_id)
    return user_data.get('default_city') if user_data else None

# --- 設定指定用戶的任意 metadata ---
def set_user_metadata(user_id: str, **kwargs: Any) -> None:
    """
    這是一個通用的函式，用於在 `meta_json` 欄位下儲存任意的鍵值對。
    """
    current_meta = get_user_metadata(user_id, "all_meta", {})
    current_meta.update(kwargs) # 使用 `.update()` 方法來合併新的數據到現有的 metadata 字典中
    _upsert_cols(user_id, meta_json=current_meta)

# --- 獲取指定用戶的某個 metadata ---
def get_user_metadata(user_id: str, key: str, default: Any = None) -> Any:
    user_data = get_user_data(user_id)
    # 處理用戶不存在的情況
    if not user_data:
        return {} if key == "all_meta" else default
    
    # 獲取整個 metadata 字典
    full_meta = user_data.get('meta_json', {})
    if key == "all_meta":
        return full_meta
        
    # 獲取特定鍵的值，如果不存在則返回預設值
    return full_meta.get(key, default)

# --- 驗證給定的城市名稱是否在有效城市列表中 ---
def is_valid_city(city_name: str) -> bool:
    return city_name in ALL_TAIWAN_COUNTIES

# --- 獲取指定用戶的推播設定 ---
def get_user_push_settings(user_id: str) -> Dict[str, bool]:
    """
    在發送推播前，為每個用戶單獨查詢，確認他們是否開啟了 FEATURE_ID (推播功能名稱)。
    """
    return get_user_metadata(user_id, "push_settings", {})

# --- 更新指定用戶的單個推播設定 ---
def update_user_push_setting(user_id: str, feature_id: str, is_enabled: bool):
    # 先讀取現有的設定，更新單個鍵值，然後再寫入回去
    # 確保只更新指定的推播功能，而不會覆蓋用戶的其他推播設定
    current_push_settings = get_user_push_settings(user_id) # 讀取
    current_push_settings[feature_id] = is_enabled # 更新
    set_user_metadata(user_id, push_settings=current_push_settings) # 寫回
    logger.info(f"用戶 {user_id} 的 {feature_id} 推播已設定為: {is_enabled}")

# --- 獲取所有開啟特定推播功能的用戶 ID ---
def get_users_with_push_enabled(feature_id: str) -> List[str]:
    """
    Firestore 查詢，尋找 meta_json.push_settings.feature_id 為 true 的用戶。
    """
    enabled_users = []

    # 使用 Firestore 的 .where() 查詢：Firestore 允許直接查詢嵌套在 Map 中的欄位
    # 必須在 Firestore 控制台為 `meta_json.push_settings.{feature_id}` 欄位建立一個複合索引，但 Firestore 預設會自動建立
    docs = users_ref.where(f'meta_json.push_settings.{feature_id}', '==', True).stream()
    
    for doc in docs:
        enabled_users.append(doc.id)
            
    return enabled_users

SYSTEM_USER_ID = "system_metadata" 

# --- 獲取系統級的元數據 ---
def get_system_metadata(key: str, default: Any = None) -> Any:
    """
    讀取上次推播的颱風 ID。
    這個函式和 `get_user_metadata` 共享底層邏輯，但使用一個固定的 `SYSTEM_USER_ID` 來存取系統級的設定。
    """
    return get_user_metadata(SYSTEM_USER_ID, key, default)

# --- 設定系統級的元數據 ---
def set_system_metadata(**kwargs: Any) -> None:
    """
    寫入這次推播的颱風 ID。
    這個函式和 `set_user_metadata` 共享底層邏輯，同樣使用 `SYSTEM_USER_ID` 來存取系統級的設定。
    """
    set_user_metadata(SYSTEM_USER_ID, **kwargs)