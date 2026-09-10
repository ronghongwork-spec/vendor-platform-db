"""
結帳日 / 應付款日計算邏輯

背景：
- 廠商資料 Excel 裡每個廠商都有自己的「結帳方式」設定（月結 或 貨到），
  用來決定一筆應付帳款是從哪一天開始被「列入這一輪要付的錢」（結帳日）。
- 實際撥款日則統一照公司規定：每月25日撥款一次。
  （廠商資料裡雖然也有「付款日」欄位，但實測資料顯示233筆廠商裡有184筆都是預設值「每月1日」，
  明顯是系統預設沒特別調整過，不能當真，所以撥款日改用公司統一規則：25日）
- 例外：如果廠商的「付款日計算方式」設定為「付款天數」（例如帳款60天），
  代表這是明確談好的個別合約天數，這種情況才會照「結帳日 + 付款天數」計算，不套用25日規則。

如果之後發現這個假設跟實際狀況對不上（例如你們其實有些廠商真的不是25日付款），
跟我說一聲，把 FIXED_PAYMENT_DAY 或例外邏輯調整一下就好，不用大改。
"""
import calendar
from datetime import date, timedelta

FIXED_PAYMENT_DAY = 25  # 公司統一每月付款日


def _last_day_of_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def _add_months(year: int, month: int, delta: int):
    m = month - 1 + delta
    y = year + m // 12
    m = m % 12 + 1
    return y, m


def _safe_date(year: int, month: int, day: int) -> date:
    day = min(day, _last_day_of_month(year, month))
    return date(year, month, day)


def compute_cutoff_date(doc_date: date, vendor) -> date | None:
    """計算這筆單據的「結帳日」：從這天起才算被列入應付帳款的這一輪"""
    if doc_date is None or vendor is None:
        return None

    if vendor.settlement_method == "貨到":
        days = vendor.delivery_days or 0
        return doc_date + timedelta(days=days)

    # 預設走月結邏輯
    day = vendor.settlement_day or 1
    offset = 1 if vendor.settlement_month_offset == "下1個月" else 0
    y, m = _add_months(doc_date.year, doc_date.month, offset)
    return _safe_date(y, m, day)


def compute_payment_date(doc_date: date, vendor) -> date | None:
    """計算這筆單據實際會在哪一天被撥款付款"""
    cutoff = compute_cutoff_date(doc_date, vendor)
    if cutoff is None:
        return None

    if vendor.payment_calc_method == "付款天數" and vendor.payment_days:
        return cutoff + timedelta(days=vendor.payment_days)

    # 公司統一每月25日撥款：抓結帳日當月的25日，如果25日已經在結帳日之前，就順延到次月25日
    pay_date = _safe_date(cutoff.year, cutoff.month, FIXED_PAYMENT_DAY)
    if pay_date < cutoff:
        y, m = _add_months(cutoff.year, cutoff.month, 1)
        pay_date = _safe_date(y, m, FIXED_PAYMENT_DAY)
    return pay_date
