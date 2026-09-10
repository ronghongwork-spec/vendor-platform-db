"""
請款期限提醒
邏輯：
1. 用廠商的「結帳方式」設定算出這筆應付帳款的「結帳日」（幾號之後才會被列入這一輪要付的錢）
2. 用「結帳日」推算「應付款日」——公司統一每月25日撥款，個別廠商如果談的是「付款天數」
   （例如帳款60天）則照那個天數算，其他都照25日規則
3. 應付款日已經過了、但這筆錢還沒被沖掉（用付款明細估算），就算「已逾期」
4. 應付款日在未來 SOON_DAYS 天以內，算「即將到期」，代表要提醒去請款/準備付款

詳細計算方式寫在 payment_calc.py，如果實際狀況跟這個假設不符，可以再調整。
"""
from datetime import date
from nicegui import ui
from database import get_session
from models import Payable, Vendor, Payment
from pages.layout import header, require_login, get_company_id
from payment_calc import compute_cutoff_date, compute_payment_date, FIXED_PAYMENT_DAY
from sqlalchemy import func

SOON_DAYS = 7  # 幾天內算「即將到期」


def render(company_code: str):
    if not require_login():
        return
    company_id = get_company_id(company_code)
    header(company_code, "reminders")

    session = get_session()
    try:
        today = date.today()

        rows_query = (
            session.query(Payable, Vendor)
            .join(Vendor, Payable.vendor_id == Vendor.id)
            .filter(Payable.company_id == company_id, Payable.doc_date.isnot(None))
            .all()
        )

        # 廠商層級已付款總額，用來粗略判斷這間廠商是否大致已經結清
        paid_by_vendor = dict(
            session.query(Payment.vendor_name_raw, func.sum(Payment.total_amt))
            .filter(Payment.company_id == company_id)
            .group_by(Payment.vendor_name_raw).all()
        )
        payable_total_by_vendor = dict(
            session.query(Payable.vendor_name_raw, func.sum(Payable.amount))
            .filter(Payable.company_id == company_id)
            .group_by(Payable.vendor_name_raw).all()
        )

        items = []
        for payable, vendor in rows_query:
            cutoff = compute_cutoff_date(payable.doc_date, vendor)
            due_date = compute_payment_date(payable.doc_date, vendor)
            if due_date is None:
                continue
            days_left = (due_date - today).days
            if days_left < 0:
                status = "已逾期"
            elif days_left <= SOON_DAYS:
                status = "即將到期"
            else:
                status = "正常"

            vendor_payable_total = payable_total_by_vendor.get(payable.vendor_name_raw, 0) or 0
            vendor_paid_total = paid_by_vendor.get(payable.vendor_name_raw, 0) or 0
            vendor_roughly_settled = vendor_paid_total >= vendor_payable_total and vendor_payable_total > 0

            items.append({
                "vendor_name": payable.vendor_name_raw,
                "invoice_no": payable.invoice_no,
                "source_no": payable.source_no,
                "doc_date": str(payable.doc_date),
                "cutoff_date": str(cutoff) if cutoff else "",
                "due_date": str(due_date),
                "days_left": days_left,
                "amount": payable.amount,
                "status": status,
                "vendor_roughly_settled": vendor_roughly_settled,
            })

        # 應付帳款裡有廠商名稱對不到廠商主檔的，列出來提醒使用者（無法計算提醒）
        vendors_without_match = (
            session.query(Payable.vendor_name_raw)
            .filter(Payable.company_id == company_id, Payable.vendor_id.is_(None))
            .distinct().all()
        )
        vendors_without_match_names = sorted({v[0] for v in vendors_without_match if v[0]})

    finally:
        session.close()

    items.sort(key=lambda r: r["days_left"])
    overdue_items = [r for r in items if r["status"] == "已逾期"]
    soon_items = [r for r in items if r["status"] == "即將到期"]
    overdue_unsettled = [r for r in overdue_items if not r["vendor_roughly_settled"]]

    with ui.column().classes("w-full p-6 gap-4"):
        ui.label("請款期限提醒").classes("text-2xl font-bold")
        ui.label(
            f"應付款日＝結帳日之後最近一次的每月{FIXED_PAYMENT_DAY}日（個別廠商如果是談定天數付款則另計）。"
            f"目前 {len(overdue_items)} 筆已逾期（其中 {len(overdue_unsettled)} 筆該廠商粗估還沒結清）、"
            f"{len(soon_items)} 筆 {SOON_DAYS} 天內到期。"
        ).classes("text-sm text-gray-500")

        with ui.row().classes("gap-4"):
            with ui.card().classes("p-4"):
                ui.label("已逾期（估未結清）").classes("text-sm text-gray-500")
                ui.label(str(len(overdue_unsettled))).classes("text-2xl font-bold text-red-600")
            with ui.card().classes("p-4"):
                ui.label(f"{SOON_DAYS} 天內到期").classes("text-sm text-gray-500")
                ui.label(str(len(soon_items))).classes("text-2xl font-bold text-orange-500")

        table = ui.table(
            columns=[
                {"name": "status", "label": "狀態", "field": "status", "align": "center"},
                {"name": "vendor_name", "label": "廠商", "field": "vendor_name", "align": "left"},
                {"name": "invoice_no", "label": "發票號碼", "field": "invoice_no", "align": "left"},
                {"name": "doc_date", "label": "單據日期", "field": "doc_date", "align": "left"},
                {"name": "cutoff_date", "label": "結帳日", "field": "cutoff_date", "align": "left"},
                {"name": "due_date", "label": "應付款日", "field": "due_date", "align": "left"},
                {"name": "days_left", "label": "剩餘天數", "field": "days_left", "align": "right"},
                {"name": "amount", "label": "金額", "field": "amount", "align": "right"},
                {"name": "vendor_roughly_settled", "label": "該廠商估已結清", "field": "vendor_roughly_settled", "align": "center"},
            ],
            rows=items,
            row_key="invoice_no",
            pagination={"rowsPerPage": 20},
        ).classes("w-full").props("dense flat bordered")
        table.add_slot(
            "body-cell-status",
            '''
            <q-td :props="props">
                <q-badge :color="props.value === '已逾期' ? 'red' : (props.value === '即將到期' ? 'orange' : 'grey')">
                    {{ props.value }}
                </q-badge>
            </q-td>
            ''',
        )
        table.add_slot(
            "body-cell-vendor_roughly_settled",
            '<q-td :props="props">{{ props.value ? "是" : "否" }}</q-td>',
        )

        if vendors_without_match_names:
            ui.separator()
            ui.label("應付帳款裡有廠商名稱對不到廠商主檔（無法計算提醒，請確認廠商簡稱是否一致）").classes(
                "text-lg font-bold mt-2 text-red-600"
            )
            ui.label("、".join(vendors_without_match_names)).classes("text-sm text-gray-600")
