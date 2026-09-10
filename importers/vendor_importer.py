"""
廠商資料匯入
來源：廠商資料YYYYMMDDHHMMSS.xlsx
欄位：序(或序號)、廠商代號、廠商簡稱、電話、傳真、聯絡人、職稱、手機、營業地址、統一編號、
      廠商全名、e-mail、帳單地址、月結日、付款日、備註、匯款帳號、
      結帳方式、貨到天數、每月結帳日、月結月、付款日計算方式、付款天數

匯入方式：整批覆蓋（跟其他三個模組一致）——每次匯入都會先清空該公司的廠商資料，
再放入這次 Excel 的全部內容。這代表：如果舊檔案有廠商A、新檔案只有廠商B，
匯入完成後系統裡就只會剩下廠商B，確保永遠是「最新一份檔案」的內容，不會有舊廠商殘留。

因為應付帳款/其他支出/付款明細會透過「廠商」欄位文字關聯到廠商主檔(vendor_id)，
覆蓋廠商資料時會先把這些關聯清空，等新廠商建好之後再依名稱重新關聯一次，
所以不用擔心刪除廠商時把其他資料搞壞。
"""
from database import get_session
from models import Vendor, Payable, Payment, ImportBatch
from importers.common import read_excel, col, to_str, to_int


def import_vendors(file_path, company_id: int, filename: str, imported_by: str) -> dict:
    df = read_excel(file_path)

    c_seq = col(df, "序號", "序")
    c_code = col(df, "廠商代號")
    c_name = col(df, "廠商簡稱")
    c_full_name = col(df, "廠商全名")
    c_phone = col(df, "電話")
    c_fax = col(df, "傳真")
    c_contact = col(df, "聯絡人")
    c_title = col(df, "職稱")
    c_mobile = col(df, "手機")
    c_email = col(df, "e-mail", "email", "Email")
    c_addr = col(df, "營業地址")
    c_billing_addr = col(df, "帳單地址")
    c_tax = col(df, "統一編號")
    c_remit = col(df, "匯款帳號")
    c_remark = col(df, "備註")
    c_settlement_method = col(df, "結帳方式")
    c_delivery_days = col(df, "貨到天數")
    c_settlement_day = col(df, "每月結帳日")
    c_settlement_month_offset = col(df, "月結月")
    c_payment_calc_method = col(df, "付款日計算方式")
    c_payment_days = col(df, "付款天數")
    c_settlement_day_label = col(df, "月結日")
    c_payment_day_label = col(df, "付款日")

    if not c_code and not c_tax:
        raise ValueError("Excel 裡找不到「廠商代號」或「統一編號」欄位，無法辨識廠商，請確認檔案格式")

    session = get_session()
    try:
        # 整批覆蓋前，先把應付帳款/付款明細的 vendor_id 關聯清空，
        # 避免刪除廠商時因為外鍵關聯而失敗（等新廠商建好後會重新關聯）
        session.query(Payable).filter(Payable.company_id == company_id).update({Payable.vendor_id: None})
        session.query(Payment).filter(Payment.company_id == company_id).update({Payment.vendor_id: None})
        session.query(Vendor).filter(Vendor.company_id == company_id).delete()

        added = 0
        for _, row in df.iterrows():
            vendor_code = to_str(row[c_code]) if c_code else None
            tax_id = to_str(row[c_tax]) if c_tax else None
            if not vendor_code and not tax_id:
                continue  # 空白列跳過

            vendor = Vendor(
                company_id=company_id,
                seq_no=to_str(row[c_seq]) if c_seq else None,
                vendor_code=vendor_code,
                vendor_name=to_str(row[c_name]) if c_name else None,
                full_name=to_str(row[c_full_name]) if c_full_name else None,
                phone=to_str(row[c_phone]) if c_phone else None,
                fax=to_str(row[c_fax]) if c_fax else None,
                contact_name=to_str(row[c_contact]) if c_contact else None,
                contact_title=to_str(row[c_title]) if c_title else None,
                mobile=to_str(row[c_mobile]) if c_mobile else None,
                email=to_str(row[c_email]) if c_email else None,
                address=to_str(row[c_addr]) if c_addr else None,
                billing_address=to_str(row[c_billing_addr]) if c_billing_addr else None,
                tax_id=tax_id,
                remit_account=to_str(row[c_remit]) if c_remit else None,
                remark=to_str(row[c_remark]) if c_remark else None,
                settlement_method=to_str(row[c_settlement_method]) if c_settlement_method else None,
                delivery_days=to_int(row[c_delivery_days]) if c_delivery_days else None,
                settlement_day=to_int(row[c_settlement_day]) if c_settlement_day else None,
                settlement_month_offset=to_str(row[c_settlement_month_offset]) if c_settlement_month_offset else None,
                payment_calc_method=to_str(row[c_payment_calc_method]) if c_payment_calc_method else None,
                payment_days=to_int(row[c_payment_days]) if c_payment_days else None,
                settlement_day_label=to_str(row[c_settlement_day_label]) if c_settlement_day_label else None,
                payment_day_label=to_str(row[c_payment_day_label]) if c_payment_day_label else None,
            )
            session.add(vendor)
            added += 1

        session.flush()

        # 重新用廠商簡稱關聯應付帳款/付款明細（因為上面全部清空重建過）
        vendor_map = {
            v.vendor_name: v.id
            for v in session.query(Vendor).filter(Vendor.company_id == company_id).all()
            if v.vendor_name
        }
        for p in session.query(Payable).filter(Payable.company_id == company_id).all():
            if p.vendor_name_raw in vendor_map:
                p.vendor_id = vendor_map[p.vendor_name_raw]
        for pm in session.query(Payment).filter(Payment.company_id == company_id).all():
            if pm.vendor_name_raw in vendor_map:
                pm.vendor_id = vendor_map[pm.vendor_name_raw]

        batch = ImportBatch(
            company_id=company_id, module="vendor", filename=filename,
            imported_by=imported_by, row_count=added,
        )
        session.add(batch)
        session.commit()
        return {"total": added}
    finally:
        session.close()
