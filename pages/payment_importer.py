"""
付款明細匯入
來源：付款明細表YYYYMMDDHHMMSS.xlsx
欄位：廠商、付款日期、付款單號、付款人、現金、轉帳、支票、其他、其他說明、付款合計、折讓、對方帳號

匯入方式：整批覆蓋（同應付帳款明細）。
注意：此表沒有發票號碼欄位，因此與應付帳款只能做「廠商層級」的勾稽（總金額比對），
無法逐筆對應到單一發票，這點在儀表板統計上已對應處理。
"""
from database import get_session
from models import Payment, Vendor, ImportBatch
from importers.common import read_excel, col, to_str, to_float, to_date


def import_payments(file_path, company_id: int, filename: str, imported_by: str) -> dict:
    df = read_excel(file_path)

    c_vendor = col(df, "廠商")
    c_date = col(df, "付款日期")
    c_no = col(df, "付款單號")
    c_payer = col(df, "付款人")
    c_cash = col(df, "現金")
    c_transfer = col(df, "轉帳")
    c_check = col(df, "支票")
    c_other = col(df, "其他")
    c_other_note = col(df, "其他說明")
    c_total = col(df, "付款合計")
    c_discount = col(df, "折讓")
    c_counter = col(df, "對方帳號")

    if not c_vendor or not c_total:
        raise ValueError("Excel 裡找不到「廠商」或「付款合計」欄位，請確認檔案格式")

    session = get_session()
    try:
        vendor_map = {
            v.vendor_name: v.id
            for v in session.query(Vendor).filter(Vendor.company_id == company_id).all()
            if v.vendor_name
        }

        session.query(Payment).filter(Payment.company_id == company_id).delete()

        batch = ImportBatch(company_id=company_id, module="payment", filename=filename, imported_by=imported_by)
        session.add(batch)
        session.flush()

        rows_added = 0
        for _, row in df.iterrows():
            vendor_name = to_str(row[c_vendor]) if c_vendor else None
            if not vendor_name:
                continue
            session.add(Payment(
                company_id=company_id,
                import_batch_id=batch.id,
                vendor_name_raw=vendor_name,
                vendor_id=vendor_map.get(vendor_name),
                payment_date=to_date(row[c_date]) if c_date else None,
                payment_no=to_str(row[c_no]) if c_no else None,
                payer=to_str(row[c_payer]) if c_payer else None,
                cash_amt=to_float(row[c_cash]) if c_cash else 0,
                transfer_amt=to_float(row[c_transfer]) if c_transfer else 0,
                check_amt=to_float(row[c_check]) if c_check else 0,
                other_amt=to_float(row[c_other]) if c_other else 0,
                other_note=to_str(row[c_other_note]) if c_other_note else None,
                total_amt=to_float(row[c_total]),
                discount_amt=to_float(row[c_discount]) if c_discount else 0,
                counter_account=to_str(row[c_counter]) if c_counter else None,
            ))
            rows_added += 1

        batch.row_count = rows_added
        session.commit()
        return {"total": rows_added}
    finally:
        session.close()
