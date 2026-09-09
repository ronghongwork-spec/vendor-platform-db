from nicegui import ui
from database import get_session
from models import OtherExpense
from pages.layout import header, require_login, get_company_id
from sqlalchemy import func


def render(company_code: str):
    if not require_login():
        return
    company_id = get_company_id(company_code)
    header(company_code, "expenses")

    with ui.column().classes("w-full p-6 gap-4"):
        ui.label("其他支出明細管理").classes("text-2xl font-bold")

        with ui.row().classes("gap-4 items-end"):
            f_keyword = ui.input(placeholder="客戶/廠商 關鍵字").classes("w-48")
            f_doc = ui.input(placeholder="單據編號").classes("w-40")
            f_date_from = ui.input(placeholder="起日 YYYY-MM-DD").classes("w-40")
            f_date_to = ui.input(placeholder="迄日 YYYY-MM-DD").classes("w-40")
            search_btn = ui.button("查詢", icon="search")

        summary_label = ui.label().classes("text-lg font-bold")

        table = ui.table(
            columns=[
                {"name": "reason", "label": "原因", "field": "reason", "align": "left"},
                {"name": "doc_date", "label": "日期", "field": "doc_date", "align": "left"},
                {"name": "doc_no", "label": "單據", "field": "doc_no", "align": "left"},
                {"name": "target_name", "label": "客戶/廠商", "field": "target_name", "align": "left"},
                {"name": "total_amount", "label": "總金額", "field": "total_amount", "align": "right"},
                {"name": "summary", "label": "摘要", "field": "summary", "align": "left"},
                {"name": "is_paid", "label": "已付款", "field": "is_paid", "align": "center"},
            ],
            rows=[],
            row_key="id",
            pagination={"rowsPerPage": 20},
        ).classes("w-full").props("dense flat bordered")
        table.add_slot(
            "body-cell-is_paid",
            '<q-td :props="props"><q-checkbox :model-value="props.value" '
            '@update:model-value="$parent.$emit(\'toggle-paid\', props.row)" /></q-td>',
        )

        def load():
            session = get_session()
            try:
                q = session.query(OtherExpense).filter(OtherExpense.company_id == company_id)
                if f_keyword.value:
                    q = q.filter(OtherExpense.target_name.ilike(f"%{f_keyword.value}%"))
                if f_doc.value:
                    q = q.filter(OtherExpense.doc_no.ilike(f"%{f_doc.value}%"))
                if f_date_from.value:
                    q = q.filter(OtherExpense.doc_date >= f_date_from.value)
                if f_date_to.value:
                    q = q.filter(OtherExpense.doc_date <= f_date_to.value)

                items = q.order_by(OtherExpense.doc_date.desc()).all()
                rows = [{
                    "id": e.id, "reason": e.reason,
                    "doc_date": str(e.doc_date) if e.doc_date else "",
                    "doc_no": e.doc_no, "target_name": e.target_name,
                    "total_amount": e.total_amount, "summary": e.summary,
                    "is_paid": bool(e.is_paid),
                } for e in items]
                table.rows = rows
                table.update()

                total = sum(r["total_amount"] or 0 for r in rows)
                unpaid = sum(r["total_amount"] or 0 for r in rows if not r["is_paid"])
                summary_label.text = f"總金額：${total:,.0f}　|　未付款：${unpaid:,.0f}（共 {len(rows)} 筆）"
            finally:
                session.close()

        def toggle_paid(e):
            row = e.args
            session = get_session()
            try:
                exp = session.query(OtherExpense).get(row["id"])
                exp.is_paid = not exp.is_paid
                session.commit()
            finally:
                session.close()
            load()

        table.on("toggle-paid", toggle_paid)
        search_btn.on_click(load)
        load()
