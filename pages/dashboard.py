from datetime import date, timedelta
from nicegui import ui
from database import get_session
from models import Payable, Payment, OtherExpense, Vendor
from pages.layout import header, require_login, get_company_id, get_company_name
from sqlalchemy import func

SOON_DAYS = 7


def render(company_code: str):
    if not require_login():
        return
    company_id = get_company_id(company_code)
    header(company_code, "dashboard")

    session = get_session()
    try:
        total_payable = session.query(func.coalesce(func.sum(Payable.amount), 0)) \
            .filter(Payable.company_id == company_id).scalar()
        total_payment = session.query(func.coalesce(func.sum(Payment.total_amt), 0)) \
            .filter(Payment.company_id == company_id).scalar()
        outstanding = total_payable - total_payment

        total_expense = session.query(func.coalesce(func.sum(OtherExpense.total_amount), 0)) \
            .filter(OtherExpense.company_id == company_id).scalar()
        unpaid_expense = session.query(func.coalesce(func.sum(OtherExpense.total_amount), 0)) \
            .filter(OtherExpense.company_id == company_id, OtherExpense.is_paid == False).scalar()  # noqa: E712

        # 請款期限提醒統計（同 reminders.py 的邏輯）
        today = date.today()
        rows_with_terms = (
            session.query(Payable.doc_date, Vendor.payment_terms_days)
            .join(Vendor, Payable.vendor_id == Vendor.id)
            .filter(
                Payable.company_id == company_id,
                Vendor.payment_terms_days.isnot(None),
                Payable.doc_date.isnot(None),
            ).all()
        )
        overdue_count, soon_count = 0, 0
        for doc_date, terms in rows_with_terms:
            days_left = (doc_date + timedelta(days=terms) - today).days
            if days_left < 0:
                overdue_count += 1
            elif days_left <= SOON_DAYS:
                soon_count += 1

        with ui.column().classes("w-full p-6 gap-6"):
            ui.label(f"{get_company_name(company_code)} — 財務總覽").classes("text-2xl font-bold")

            with ui.row().classes("gap-4 w-full"):
                _stat_card("應付帳款總額", total_payable, "receipt_long", "text-blue-600")
                _stat_card("累計已付款", total_payment, "account_balance_wallet", "text-green-600")
                _stat_card("尚未付款金額（估）", outstanding, "warning", "text-red-600")
                _stat_card("其他支出未付款", unpaid_expense, "payments", "text-orange-600")

            with ui.row().classes("gap-4 w-full"):
                with ui.card().classes("flex-1 p-4 cursor-pointer") \
                        .on("click", lambda: ui.navigate.to(f"/c/{company_code}/reminders")):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("notifications_active").classes("text-2xl text-red-600")
                        ui.label("請款已逾期").classes("text-sm text-gray-500")
                    ui.label(f"{overdue_count} 筆").classes("text-2xl font-bold text-red-600")
                with ui.card().classes("flex-1 p-4 cursor-pointer") \
                        .on("click", lambda: ui.navigate.to(f"/c/{company_code}/reminders")):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("schedule").classes("text-2xl text-orange-500")
                        ui.label(f"{SOON_DAYS}天內到期").classes("text-sm text-gray-500")
                    ui.label(f"{soon_count} 筆").classes("text-2xl font-bold text-orange-500")

            ui.label(
                "提醒：「尚未付款金額」是用【應付帳款總額】-【累計已付款】估算，"
                "因為付款明細沒有逐筆對應發票號碼，僅能做廠商/公司層級的勾稽，無法保證每筆都精準對應。"
            ).classes("text-sm text-gray-500")

            ui.label("各廠商應付帳款彙總").classes("text-lg font-bold mt-4")
            vendor_rows = session.query(
                Payable.vendor_name_raw,
                func.sum(Payable.amount).label("payable_total"),
            ).filter(Payable.company_id == company_id) \
                .group_by(Payable.vendor_name_raw).all()

            payment_by_vendor = dict(
                session.query(Payment.vendor_name_raw, func.sum(Payment.total_amt))
                .filter(Payment.company_id == company_id)
                .group_by(Payment.vendor_name_raw).all()
            )

            table_rows = []
            for vendor_name, payable_total in vendor_rows:
                paid = payment_by_vendor.get(vendor_name, 0) or 0
                table_rows.append({
                    "廠商": vendor_name,
                    "應付總額": round(payable_total or 0, 0),
                    "已付款": round(paid, 0),
                    "估計未付": round((payable_total or 0) - paid, 0),
                })
            table_rows.sort(key=lambda r: r["估計未付"], reverse=True)

            ui.table(
                columns=[
                    {"name": "廠商", "label": "廠商", "field": "廠商", "align": "left"},
                    {"name": "應付總額", "label": "應付總額", "field": "應付總額", "align": "right"},
                    {"name": "已付款", "label": "已付款", "field": "已付款", "align": "right"},
                    {"name": "估計未付", "label": "估計未付", "field": "估計未付", "align": "right"},
                ],
                rows=table_rows,
                row_key="廠商",
            ).classes("w-full").props("dense flat bordered")
    finally:
        session.close()


def _stat_card(title, value, icon, color_class):
    with ui.card().classes("flex-1 p-4"):
        with ui.row().classes("items-center gap-2"):
            ui.icon(icon).classes(f"text-2xl {color_class}")
            ui.label(title).classes("text-sm text-gray-500")
        ui.label(f"${value:,.0f}").classes(f"text-2xl font-bold {color_class}")
