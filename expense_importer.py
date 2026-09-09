"""
其他支出明細匯入
來源：其他支出明細表YYYYMMDDHHMMSS.xlsx
欄位：原因、日期、單據、客戶/廠商、未稅金額、稅額、總金額、摘要

匯入方式：整批覆蓋（同應付帳款明細，視為當下快照）。
注意：來源 Excel 沒有「是否已付款」欄位，匯入後 is_paid 一律預設為未付款，
需要在畫面上手動勾選已付款，或之後串上其他資料源自動比對。
"""
from database import get_session
from models import OtherExpense, ImportBatch
from importers.common import read_excel, col, to_str, to_float, to_date


def import_expenses(file_path, company_id: int, filename: str, imported_by: str) -> dict:
    df = read_excel(file_path)

    c_reason = col(df, "原因")
    c_date = col(df, "日期")
    c_doc = col(df, "單據")
    c_target = col(df, "客戶/廠商", "客戶／廠商", "客戶廠商")
    c_untaxed = col(df, "未稅金額")
    c_tax = col(df, "稅額")
    c_total = col(df, "總金額")
    c_summary = col(df, "摘要")

    if not c_total:
        raise ValueError("Excel 裡找不到「總金額」欄位，請確認檔案格式")

    session = get_session()
    try:
        session.query(OtherExpense).filter(OtherExpense.company_id == company_id).delete()

        batch = ImportBatch(company_id=company_id, module="expense", filename=filename, imported_by=imported_by)
        session.add(batch)
        session.flush()

        rows_added = 0
        for _, row in df.iterrows():
            total = to_float(row[c_total]) if c_total else 0
            target = to_str(row[c_target]) if c_target else None
            if total == 0 and not target:
                continue
            session.add(OtherExpense(
                company_id=company_id,
                import_batch_id=batch.id,
                reason=to_str(row[c_reason]) if c_reason else None,
                doc_date=to_date(row[c_date]) if c_date else None,
                doc_no=to_str(row[c_doc]) if c_doc else None,
                target_name=target,
                amount_untaxed=to_float(row[c_untaxed]) if c_untaxed else None,
                tax_amount=to_float(row[c_tax]) if c_tax else None,
                total_amount=total,
                summary=to_str(row[c_summary]) if c_summary else None,
            ))
            rows_added += 1

        batch.row_count = rows_added
        session.commit()
        return {"total": rows_added}
    finally:
        session.close()
