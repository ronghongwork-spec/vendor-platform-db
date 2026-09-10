from nicegui import ui
from database import get_session
from models import Vendor
from pages.layout import header, require_login, get_company_id


def _settlement_summary(v: Vendor) -> str:
    """把結帳/付款規則組成一句話方便在表格裡看"""
    if v.settlement_method == "貨到":
        base = f"貨到後{v.delivery_days or 0}天結帳"
    else:
        day_text = "月底" if (v.settlement_day or 0) >= 31 else f"{v.settlement_day}日"
        month_text = "本月" if v.settlement_month_offset != "下1個月" else "次月"
        base = f"月結：{month_text}{day_text}"
    if v.payment_calc_method == "付款天數" and v.payment_days:
        pay = f"結帳後{v.payment_days}天付款"
    else:
        pay = "每月25日付款"
    return f"{base}，{pay}"


def render(company_code: str):
    if not require_login():
        return
    company_id = get_company_id(company_code)
    header(company_code, "vendors")

    with ui.column().classes("w-full p-6 gap-4"):
        ui.label("廠商資料管理").classes("text-2xl font-bold")
        ui.label(
            "輸入廠商代號、簡稱或統一編號可即時篩選。資料主要透過「匯入資料」頁批次匯入（每次匯入會整批覆蓋成最新內容），"
            "這裡也可以手動修改單一廠商的資料。"
        ).classes("text-sm text-gray-500")

        search = ui.input(placeholder="搜尋廠商代號 / 簡稱 / 統一編號").classes("w-96")
        table = ui.table(
            columns=[
                {"name": "vendor_code", "label": "廠商代號", "field": "vendor_code", "align": "left"},
                {"name": "vendor_name", "label": "廠商簡稱", "field": "vendor_name", "align": "left"},
                {"name": "contact_name", "label": "聯絡人", "field": "contact_name", "align": "left"},
                {"name": "phone", "label": "電話", "field": "phone", "align": "left"},
                {"name": "mobile", "label": "手機", "field": "mobile", "align": "left"},
                {"name": "tax_id", "label": "統一編號", "field": "tax_id", "align": "left"},
                {"name": "settlement_summary", "label": "結帳/付款規則", "field": "settlement_summary", "align": "left"},
                {"name": "remit_account", "label": "匯款帳號", "field": "remit_account", "align": "left"},
            ],
            rows=[],
            row_key="id",
        ).classes("w-full").props("dense flat bordered")
        table.add_slot(
            "body-cell-vendor_code",
            '<q-td :props="props"><a class="text-primary cursor-pointer" '
            '@click="$parent.$emit(\'edit-row\', props.row)">{{ props.value }}</a></q-td>',
        )

        def load(keyword: str = ""):
            session = get_session()
            try:
                q = session.query(Vendor).filter(Vendor.company_id == company_id)
                if keyword:
                    like = f"%{keyword}%"
                    q = q.filter(
                        (Vendor.vendor_code.ilike(like))
                        | (Vendor.vendor_name.ilike(like))
                        | (Vendor.tax_id.ilike(like))
                    )
                rows = []
                for v in q.order_by(Vendor.vendor_code).all():
                    rows.append({
                        "id": v.id, "vendor_code": v.vendor_code, "vendor_name": v.vendor_name,
                        "contact_name": v.contact_name, "phone": v.phone, "mobile": v.mobile,
                        "tax_id": v.tax_id, "remit_account": v.remit_account,
                        "settlement_summary": _settlement_summary(v),
                    })
                table.rows = rows
                table.update()
            finally:
                session.close()

        search.on("update:model-value", lambda e: load(search.value))

        def open_edit_dialog(row):
            session = get_session()
            try:
                vendor = session.query(Vendor).get(row["id"]) if row else None
                with ui.dialog() as dialog, ui.card().classes("w-[600px] max-w-full"):
                    ui.label("編輯廠商").classes("text-lg font-bold")

                    with ui.row().classes("w-full gap-2"):
                        f_code = ui.input("廠商代號", value=vendor.vendor_code).classes("flex-1")
                        f_name = ui.input("廠商簡稱", value=vendor.vendor_name).classes("flex-1")
                    with ui.row().classes("w-full gap-2"):
                        f_contact = ui.input("聯絡人", value=vendor.contact_name).classes("flex-1")
                        f_phone = ui.input("電話", value=vendor.phone).classes("flex-1")
                        f_mobile = ui.input("手機", value=vendor.mobile).classes("flex-1")
                    with ui.row().classes("w-full gap-2"):
                        f_tax = ui.input("統一編號", value=vendor.tax_id).classes("flex-1")
                        f_remit = ui.input("匯款帳號", value=vendor.remit_account).classes("flex-1")
                    f_addr = ui.input("營業地址", value=vendor.address).classes("w-full")

                    ui.label("結帳/付款規則").classes("font-bold mt-2")
                    with ui.row().classes("w-full gap-2 items-end"):
                        f_settle_method = ui.select(
                            ["月結", "貨到"], label="結帳方式",
                            value=vendor.settlement_method or "月結",
                        ).classes("flex-1")
                        f_delivery_days = ui.number(
                            "貨到天數（結帳方式=貨到時使用）", value=vendor.delivery_days or 0,
                        ).classes("flex-1")
                    with ui.row().classes("w-full gap-2 items-end"):
                        f_settle_day = ui.number(
                            "每月結帳日（1~31，31代表月底）", value=vendor.settlement_day or 1,
                        ).classes("flex-1")
                        f_settle_offset = ui.select(
                            ["本月", "下1個月"], label="月結月",
                            value=vendor.settlement_month_offset or "本月",
                        ).classes("flex-1")
                    with ui.row().classes("w-full gap-2 items-end"):
                        f_pay_method = ui.select(
                            ["每月付款日", "付款天數"], label="付款日計算方式",
                            value=vendor.payment_calc_method or "每月付款日",
                        ).classes("flex-1")
                        f_pay_days = ui.number(
                            "付款天數（付款日計算方式=付款天數時使用）", value=vendor.payment_days or 0,
                        ).classes("flex-1")
                    ui.label(
                        "「每月付款日」統一照公司規則每月25日撥款；只有選「付款天數」時才會用「結帳日+付款天數」計算。"
                    ).classes("text-xs text-gray-400")

                    def save():
                        s2 = get_session()
                        try:
                            v = s2.query(Vendor).get(row["id"])
                            v.vendor_code = f_code.value
                            v.vendor_name = f_name.value
                            v.contact_name = f_contact.value
                            v.phone = f_phone.value
                            v.mobile = f_mobile.value
                            v.tax_id = f_tax.value
                            v.remit_account = f_remit.value
                            v.address = f_addr.value
                            v.settlement_method = f_settle_method.value
                            v.delivery_days = int(f_delivery_days.value or 0)
                            v.settlement_day = int(f_settle_day.value or 1)
                            v.settlement_month_offset = f_settle_offset.value
                            v.payment_calc_method = f_pay_method.value
                            v.payment_days = int(f_pay_days.value or 0)
                            s2.commit()
                        finally:
                            s2.close()
                        dialog.close()
                        load(search.value)

                    with ui.row().classes("justify-end w-full gap-2 mt-4"):
                        ui.button("取消", on_click=dialog.close).props("flat")
                        ui.button("儲存", on_click=save)
                dialog.open()
            finally:
                session.close()

        table.on("edit-row", lambda e: open_edit_dialog(e.args))
        load()
