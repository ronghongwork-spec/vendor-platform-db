from nicegui import ui
from database import get_session
from models import Payable
from pages.layout import header, require_login, get_company_id
from sqlalchemy import func


def render(company_code: str):
    if not require_login():
        return
    company_id = get_company_id(company_code)
    header(company_code, "payables")

    with ui.column().classes("w-full p-6 gap-4"):
        ui.label("應付帳款明細管理").classes("text-2xl font-bold")

        with ui.row().classes("gap-4 items-end"):
            f_keyword = ui.input(placeholder="廠商關鍵字").classes("w-48")
            f_invoice = ui.input(placeholder="發票號碼").classes("w-40")
            f_source = ui.input(placeholder="來源單號").classes("w-40")
            f_date_from = ui.input(placeholder="起日 YYYY-MM-DD").classes("w-40")
            f_date_to = ui.input(placeholder="迄日 YYYY-MM-DD").classes("w-40")
            search_btn = ui.button("查詢", icon="search")

        total_label = ui.label().classes("text-lg font-bold text-red-600")

        table = ui.table(
            columns=[
                {"name": "vendor_name_raw", "label": "廠商", "field": "vendor_name_raw", "align": "left"},
                {"name": "doc_date", "label": "單據日期", "field": "doc_date", "align": "left"},
                {"name": "source_no", "label": "來源單號", "field": "source_no", "align": "left"},
                {"name": "invoice_no", "label": "發票號碼", "field": "invoice_no", "align": "left"},
                {"name": "item_name", "label": "品名", "field": "item_name", "align": "left"},
                {"name": "qty", "label": "數量", "field": "qty", "align": "right"},
                {"name": "unit_price", "label": "單價", "field": "unit_price", "align": "right"},
                {"name": "amount", "label": "金額", "field": "amount", "align": "right"},
                {"name": "handler", "label": "經辦人", "field": "handler", "align": "left"},
            ],
            rows=[],
            row_key="id",
            pagination={"rowsPerPage": 20},
        ).classes("w-full").props("dense flat bordered")

        def load():
            session = get_session()
            try:
                q = session.query(Payable).filter(Payable.company_id == company_id)
                if f_keyword.value:
                    q = q.filter(Payable.vendor_name_raw.ilike(f"%{f_keyword.value}%"))
                if f_invoice.value:
                    q = q.filter(Payable.invoice_no.ilike(f"%{f_invoice.value}%"))
                if f_source.value:
                    q = q.filter(Payable.source_no.ilike(f"%{f_source.value}%"))
                if f_date_from.value:
                    q = q.filter(Payable.doc_date >= f_date_from.value)
                if f_date_to.value:
                    q = q.filter(Payable.doc_date <= f_date_to.value)

                rows = []
                for p in q.order_by(Payable.doc_date.desc()).all():
                    rows.append({
                        "id": p.id, "vendor_name_raw": p.vendor_name_raw,
                        "doc_date": str(p.doc_date) if p.doc_date else "",
                        "source_no": p.source_no, "invoice_no": p.invoice_no,
                        "item_name": p.item_name, "qty": p.qty, "unit_price": p.unit_price,
                        "amount": p.amount, "handler": p.handler,
                    })
                table.rows = rows
                table.update()

                total = q.with_entities(func.coalesce(func.sum(Payable.amount), 0)).scalar()
                total_label.text = f"目前篩選結果總金額：${total:,.0f}（共 {len(rows)} 筆）"
            finally:
                session.close()

        search_btn.on_click(load)
        load()
