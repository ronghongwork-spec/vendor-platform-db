import pandas as pd


def read_excel(file_path_or_buffer) -> pd.DataFrame:
    """讀取 Excel，欄位名稱去除前後空白，避免 A1 匯出檔常見的多餘空格造成對不到欄位"""
    df = pd.read_excel(file_path_or_buffer)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def col(df: pd.DataFrame, *candidates):
    """回傳第一個存在於 df 的候選欄位名稱；都找不到回傳 None（讓呼叫端決定要不要報錯）"""
    for c in candidates:
        if c in df.columns:
            return c
    return None


def to_float(v, default=0.0):
    try:
        if pd.isna(v):
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def to_int(v, default=None):
    try:
        if pd.isna(v):
            return default
        return int(float(v))
    except (TypeError, ValueError):
        return default


def to_date(v):
    if pd.isna(v):
        return None
    try:
        return pd.to_datetime(v).date()
    except Exception:
        return None


def to_str(v):
    if pd.isna(v):
        return None
    s = str(v).strip()
    return s or None
