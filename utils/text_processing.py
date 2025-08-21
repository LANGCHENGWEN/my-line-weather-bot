# utils/text_processing.py
"""
文字處理工具模組，標準化和清理用戶輸入的文字資料。
確保不同寫法的相同詞彙（例如「台」和「臺」）在程式碼中被統一處理，避免因文字不匹配而導致的錯誤。
將這些處理邏輯集中在一個模組中，可以提高程式碼的可重用性和維護性。
"""
def normalize_city_name(city_name: str) -> str:
    """
    將常見的縣市名稱替換為標準格式，例如把「台」改成「臺」。
    特別處理「台」與「臺」這兩種常見的寫法，將前者統一替換為後者，確保後續的資料庫查詢或邏輯判斷能夠準確匹配。
    """
    if not city_name: # 先檢查輸入是否為空；如果 `city_name` 是 `None` 或空字串，直接返回，避免後續操作引發錯誤
        return city_name
    return city_name.replace("台", "臺")