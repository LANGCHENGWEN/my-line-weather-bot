def normalize_city_name(city_name: str) -> str:
    """
    將常見的縣市名稱替換為標準格式，例如把「台」改成「臺」。
    """
    if not city_name:
        return city_name
    return city_name.replace("台", "臺")