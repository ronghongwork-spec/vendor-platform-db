from nicegui import ui
from database import get_session
from models import Payment
from pages.layout import header, require_login, get_company_id
from sqlalchemy import func


def render(company_code: str):
    if not require_login():
        return
    company_id = get_company_id(company_code)
    header(company_code, "payments")

    with ui.column().classes("w-full p-6 gap-4"):
        ui.label("付款明細管理").classes("text-2xl font-bold")

        with ui.row().classes("gap-4 items-end"):
            f_keyword = ui.input(placeholder="廠商關鍵字").classes("w-48")
            f_no = ui.input(placeholder="付款單號").classes("w-40")
            f_date_from = ui.input(placeholder="起日 YYYY-MM-DD").classes("w-40")
            f_date_to = ui.input(placeholder="迄日 YYYY-MM-DD").classes("w-40")
            search_btn = ui.button("查詢", icon="search")

        summary_label = ui.label().classes("text-lg font-bold")

        table = ui.table(
            columns=[
                {"name": "vendor_name_raw", "label": "廠商", "field": "vendor_name_raw", "align": "left"},
                {"name": "payment_date", "label": "付款日期", "field": "payment_date", "align": "left"},
                {"name": "payment_no", "label": "付款單號", "field": "payment_no", "align": "left"},
                {"name": "cash_amt", "label": "現金", "field": "cash_amt", "align": "right"},
                {"name": "transfer_amt", "label": "轉帳", "field": "transfer_amt", "align": "right"},
                {"name": "check_amt", "label": "支票", "field": "check_amt", "align": "right"},
                {"name": "other_amt", "label": "其他", "field": "other_amt", "align": "right"},
                {"name": "total_amt", "label": "付款合計", "field": "total_amt", "align": "right"},
                {"name": "discount_amt", "label": "折讓", "field": "discount_amt", "align": "right"},
                {"name": "payer", "label": "付款人", "field": "payer", "align": "left"},
            ],
            rows=[],
            row_key="id",
            pagination={"rowsPerPage": 20},
        ).classes("w-full").props("dense flat bordered")

        def load():
            session = get_session()
            try:
                q = session.query(Payment).filter(Payment.company_id == company_id)
                if f_keyword.value:
                    q = q.filter(Payment.vendor_name_raw.ilike(f"%{f_keyword.value}%"))
                if f_no.value:
                    q = q.filter(Payment.payment_no.ilike(f"%{f_no.value}%"))
                if f_date_from.value:
                    q = q.filter(Payment.payment_date >= f_date_from.value)
                if f_date_to.value:
                    q = q.filter(Payment.payment_date <= f_date_to.value)

                items = q.order_by(Payment.payment_date.desc()).all()
                rows = [{
                    "id": p.id, "vendor_name_raw": p.vendor_name_raw,
                    "payment_date": str(p.payment_date) if p.payment_date else "",
                    "payment_no": p.payment_no, "cash_amt": p.cash_amt, "transfer_amt": p.transfer_amt,
                    "check_amt": p.check_amt, "other_amt": p.other_amt, "total_amt": p.total_amt,
                    "discount_amt": p.discount_amt, "payer": p.payer,
                } for p in items]
                table.rows = rows
                table.update()

                by_channel = {"現金": 0, "轉帳": 0, "支票": 0, "其他": 0}
                for r in rows:
                    by_channel["現金"] += r["cash_amt"] or 0
                    by_channel["轉帳"] += r["transfer_amt"] or 0
                    by_channel["支票"] += r["check_amt"] or 0
                    by_channel["其他"] += r["other_amt"] or 0
                total = sum(r["total_amt"] or 0 for r in rows)
                summary_label.text = (
                    f"付款總計：${total:,.0f}（共 {len(rows)} 筆） | "
                    f"現金 ${by_channel['現金']:,.0f} / 轉帳 ${by_channel['轉帳']:,.0f} / "
                    f"支票 ${by_channel['支票']:,.0f} / 其他 ${by_channel['其他']:,.0f}"
                )
            finally:
                session.close()

        search_btn.on_click(load)
        load()
