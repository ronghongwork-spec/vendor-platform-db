"""
請款期限提醒
邏輯：截止日 = 應付帳款明細的「單據日期」+ 廠商主檔設定的「月結天數」
- 沒有設定月結天數的廠商，不會出現在提醒清單，畫面上會另外列出「尚未設定月結天數」的廠商，
  方便使用者知道要去廠商資料頁補設定。
- 因為系統沒有「這筆應付帳款是否已請款/已付款」的欄位（付款明細沒有逐筆對應發票號碼），
  這裡列出的是「距離截止日還有多久」，不代表這筆一定還沒處理，僅供提醒用途。
"""
from datetime import date, timedelta
from nicegui import ui
from database import get_session
from models import Payable, Vendor
from pages.layout import header, require_login, get_company_id

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
            .filter(
                Payable.company_id == company_id,
                Vendor.payment_terms_days.isnot(None),
                Payable.doc_date.isnot(None),
            )
            .all()
        )

        items = []
        for payable, vendor in rows_query:
            due_date = payable.doc_date + timedelta(days=vendor.payment_terms_days)
            days_left = (due_date - today).days
            if days_left < 0:
                status = "已逾期"
            elif days_left <= SOON_DAYS:
                status = "即將到期"
            else:
                status = "正常"
            items.append({
                "vendor_name": payable.vendor_name_raw,
                "invoice_no": payable.invoice_no,
                "source_no": payable.source_no,
                "doc_date": str(payable.doc_date),
                "payment_terms_days": vendor.payment_terms_days,
                "due_date": str(due_date),
                "days_left": days_left,
                "amount": payable.amount,
                "status": status,
            })

        # 沒設定月結天數的廠商（但有應付帳款資料），列出來提醒使用者去補設定
        vendors_without_terms = (
            session.query(Payable.vendor_name_raw)
            .filter(Payable.company_id == company_id, Payable.vendor_id.is_(None))
            .distinct()
            .all()
        )
        vendors_without_terms_names = sorted({v[0] for v in vendors_without_terms if v[0]})

        vendors_missing_terms_set = (
            session.query(Vendor.vendor_name)
            .filter(Vendor.company_id == company_id, Vendor.payment_terms_days.is_(None))
            .all()
        )
        vendors_missing_terms_names = sorted({v[0] for v in vendors_missing_terms_set if v[0]})

    finally:
        session.close()

    items.sort(key=lambda r: r["days_left"])
    overdue_count = sum(1 for r in items if r["status"] == "已逾期")
    soon_count = sum(1 for r in items if r["status"] == "即將到期")

    with ui.column().classes("w-full p-6 gap-4"):
        ui.label("請款期限提醒").classes("text-2xl font-bold")
        ui.label(
            f"截止日 = 單據日期 + 廠商月結天數（在「廠商資料」頁可以設定）。"
            f"目前有 {overdue_count} 筆已逾期、{soon_count} 筆 {SOON_DAYS} 天內到期。"
        ).classes("text-sm text-gray-500")

        with ui.row().classes("gap-4"):
            with ui.card().classes("p-4"):
                ui.label("已逾期").classes("text-sm text-gray-500")
                ui.label(str(overdue_count)).classes("text-2xl font-bold text-red-600")
            with ui.card().classes("p-4"):
                ui.label(f"{SOON_DAYS} 天內到期").classes("text-sm text-gray-500")
                ui.label(str(soon_count)).classes("text-2xl font-bold text-orange-500")

        table = ui.table(
            columns=[
                {"name": "status", "label": "狀態", "field": "status", "align": "center"},
                {"name": "vendor_name", "label": "廠商", "field": "vendor_name", "align": "left"},
                {"name": "invoice_no", "label": "發票號碼", "field": "invoice_no", "align": "left"},
                {"name": "source_no", "label": "來源單號", "field": "source_no", "align": "left"},
                {"name": "doc_date", "label": "單據日期", "field": "doc_date", "align": "left"},
                {"name": "payment_terms_days", "label": "月結天數", "field": "payment_terms_days", "align": "right"},
                {"name": "due_date", "label": "截止日", "field": "due_date", "align": "left"},
                {"name": "days_left", "label": "剩餘天數", "field": "days_left", "align": "right"},
                {"name": "amount", "label": "金額", "field": "amount", "align": "right"},
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

        if vendors_missing_terms_names:
            ui.separator()
            ui.label("尚未設定月結天數的廠商（不會出現在上面的提醒清單）").classes("text-lg font-bold mt-2")
            ui.label("、".join(vendors_missing_terms_names)).classes("text-sm text-gray-600")

        if vendors_without_terms_names:
            ui.separator()
            ui.label("應付帳款裡有廠商名稱對不到廠商主檔（無法計算提醒，請確認廠商簡稱是否一致）").classes(
                "text-lg font-bold mt-2 text-red-600"
            )
            ui.label("、".join(vendors_without_terms_names)).classes("text-sm text-gray-600")
