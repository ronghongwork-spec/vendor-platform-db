"""
應付帳款明細匯入
來源：應付帳款明細表YYYYMMDDHHMMSS.xlsx
欄位：廠商、單據日期、來源單號、經辦人、發票號碼、品號、品名、數量、單位、單價、金額、匯款帳號

匯入方式：整批覆蓋 —— 因為這張表通常是 A1 當下的「應付帳款現況」快照，
所以每次匯入會先刪除該公司舊資料，再放入這次匯入的內容，確保「未付金額」統計是最新的。
如果之後需要保留歷史軌跡，可以改成不刪除、只累加，並改用 import_batch_id 篩選「最新一批」。
"""
from database import get_session
from models import Payable, Vendor, ImportBatch
from importers.common import read_excel, col, to_str, to_float, to_date


def import_payables(file_path, company_id: int, filename: str, imported_by: str) -> dict:
    df = read_excel(file_path)

    c_vendor = col(df, "廠商")
    c_date = col(df, "單據日期")
    c_source = col(df, "來源單號")
    c_handler = col(df, "經辦人")
    c_invoice = col(df, "發票號碼")
    c_item_no = col(df, "品號")
    c_item_name = col(df, "品名")
    c_qty = col(df, "數量")
    c_unit = col(df, "單位")
    c_price = col(df, "單價")
    c_amount = col(df, "金額")
    c_remit = col(df, "匯款帳號")

    if not c_vendor or not c_amount:
        raise ValueError("Excel 裡找不到「廠商」或「金額」欄位，請確認檔案格式")

    session = get_session()
    try:
        # 建立廠商名稱 -> vendor_id 對照表，方便帶入廠商主檔資訊
        vendor_map = {
            v.vendor_name: v.id
            for v in session.query(Vendor).filter(Vendor.company_id == company_id).all()
            if v.vendor_name
        }

        # 整批覆蓋：先刪掉這間公司舊的應付帳款資料
        session.query(Payable).filter(Payable.company_id == company_id).delete()

        batch = ImportBatch(company_id=company_id, module="payable", filename=filename, imported_by=imported_by)
        session.add(batch)
        session.flush()  # 取得 batch.id

        rows_added = 0
        for _, row in df.iterrows():
            vendor_name = to_str(row[c_vendor]) if c_vendor else None
            if not vendor_name:
                continue
            session.add(Payable(
                company_id=company_id,
                import_batch_id=batch.id,
                vendor_name_raw=vendor_name,
                vendor_id=vendor_map.get(vendor_name),
                doc_date=to_date(row[c_date]) if c_date else None,
                source_no=to_str(row[c_source]) if c_source else None,
                handler=to_str(row[c_handler]) if c_handler else None,
                invoice_no=to_str(row[c_invoice]) if c_invoice else None,
                item_no=to_str(row[c_item_no]) if c_item_no else None,
                item_name=to_str(row[c_item_name]) if c_item_name else None,
                qty=to_float(row[c_qty]) if c_qty else None,
                unit=to_str(row[c_unit]) if c_unit else None,
                unit_price=to_float(row[c_price]) if c_price else None,
                amount=to_float(row[c_amount]),
                remit_account=to_str(row[c_remit]) if c_remit else None,
            ))
            rows_added += 1

        batch.row_count = rows_added
        session.commit()
        return {"total": rows_added}
    finally:
        session.close()
