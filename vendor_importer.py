"""
廠商資料匯入
來源：廠商資料YYYYMMDDHHMMSS.xlsx
欄位：序號、廠商代號、廠商簡稱、電話、傳真、聯絡人、職稱、手機、營業地址、統一編號

匯入方式：以「廠商代號」為 key 做 upsert（新增或更新），不會刪除既有廠商，
因為廠商主檔通常是持續累積、不會整批被取代。
"""
from database import get_session
from models import Vendor, ImportBatch
from importers.common import read_excel, col, to_str


def import_vendors(file_path, company_id: int, filename: str, imported_by: str) -> dict:
    df = read_excel(file_path)

    c_seq = col(df, "序號")
    c_code = col(df, "廠商代號")
    c_name = col(df, "廠商簡稱")
    c_phone = col(df, "電話")
    c_fax = col(df, "傳真")
    c_contact = col(df, "聯絡人")
    c_title = col(df, "職稱")
    c_mobile = col(df, "手機")
    c_addr = col(df, "營業地址")
    c_tax = col(df, "統一編號")

    if not c_code and not c_tax:
        raise ValueError("Excel 裡找不到「廠商代號」或「統一編號」欄位，無法辨識廠商，請確認檔案格式")

    session = get_session()
    added, updated = 0, 0
    try:
        for _, row in df.iterrows():
            vendor_code = to_str(row[c_code]) if c_code else None
            tax_id = to_str(row[c_tax]) if c_tax else None
            if not vendor_code and not tax_id:
                continue  # 空白列跳過

            query = session.query(Vendor).filter(Vendor.company_id == company_id)
            vendor = None
            if vendor_code:
                vendor = query.filter(Vendor.vendor_code == vendor_code).first()
            if not vendor and tax_id:
                vendor = query.filter(Vendor.tax_id == tax_id).first()

            is_new = vendor is None
            if is_new:
                vendor = Vendor(company_id=company_id)
                session.add(vendor)

            vendor.seq_no = to_str(row[c_seq]) if c_seq else vendor.seq_no
            vendor.vendor_code = vendor_code or vendor.vendor_code
            vendor.vendor_name = to_str(row[c_name]) if c_name else vendor.vendor_name
            vendor.phone = to_str(row[c_phone]) if c_phone else vendor.phone
            vendor.fax = to_str(row[c_fax]) if c_fax else vendor.fax
            vendor.contact_name = to_str(row[c_contact]) if c_contact else vendor.contact_name
            vendor.contact_title = to_str(row[c_title]) if c_title else vendor.contact_title
            vendor.mobile = to_str(row[c_mobile]) if c_mobile else vendor.mobile
            vendor.address = to_str(row[c_addr]) if c_addr else vendor.address
            vendor.tax_id = tax_id or vendor.tax_id

            if is_new:
                added += 1
            else:
                updated += 1

        batch = ImportBatch(
            company_id=company_id, module="vendor", filename=filename,
            imported_by=imported_by, row_count=added + updated,
        )
        session.add(batch)
        session.commit()
        return {"added": added, "updated": updated, "total": added + updated}
    finally:
        session.close()
