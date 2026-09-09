from nicegui import ui
from database import get_session
from models import Vendor
from pages.layout import header, require_login, get_company_id


def render(company_code: str):
    if not require_login():
        return
    company_id = get_company_id(company_code)
    header(company_code, "vendors")

    with ui.column().classes("w-full p-6 gap-4"):
        ui.label("廠商資料管理").classes("text-2xl font-bold")
        ui.label("輸入廠商代號、簡稱或統一編號可即時篩選；資料主要透過「匯入資料」頁批次匯入，這裡也可手動新增/修改。").classes("text-sm text-gray-500")

        search = ui.input(placeholder="搜尋廠商代號 / 簡稱 / 統一編號").classes("w-96")
        table = ui.table(
            columns=[
                {"name": "vendor_code", "label": "廠商代號", "field": "vendor_code", "align": "left"},
                {"name": "vendor_name", "label": "廠商簡稱", "field": "vendor_name", "align": "left"},
                {"name": "contact_name", "label": "聯絡人", "field": "contact_name", "align": "left"},
                {"name": "contact_title", "label": "職稱", "field": "contact_title", "align": "left"},
                {"name": "phone", "label": "電話", "field": "phone", "align": "left"},
                {"name": "mobile", "label": "手機", "field": "mobile", "align": "left"},
                {"name": "tax_id", "label": "統一編號", "field": "tax_id", "align": "left"},
                {"name": "payment_terms_days", "label": "月結天數", "field": "payment_terms_days", "align": "right"},
                {"name": "address", "label": "營業地址", "field": "address", "align": "left"},
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
                        "contact_name": v.contact_name, "contact_title": v.contact_title,
                        "phone": v.phone, "mobile": v.mobile, "tax_id": v.tax_id, "address": v.address,
                        "payment_terms_days": v.payment_terms_days,
                    })
                table.rows = rows
                table.update()
            finally:
                session.close()

        search.on("update:model-value", lambda e: load(search.value))
        ui.button("新增廠商", icon="add", on_click=lambda: open_edit_dialog(None))

        def open_edit_dialog(row):
            session = get_session()
            try:
                vendor = session.query(Vendor).get(row["id"]) if row else None
                with ui.dialog() as dialog, ui.card().classes("w-96"):
                    ui.label("編輯廠商" if vendor else "新增廠商").classes("text-lg font-bold")
                    f_code = ui.input("廠商代號", value=vendor.vendor_code if vendor else "")
                    f_name = ui.input("廠商簡稱", value=vendor.vendor_name if vendor else "")
                    f_contact = ui.input("聯絡人", value=vendor.contact_name if vendor else "")
                    f_title = ui.input("職稱", value=vendor.contact_title if vendor else "")
                    f_phone = ui.input("電話", value=vendor.phone if vendor else "")
                    f_mobile = ui.input("手機", value=vendor.mobile if vendor else "")
                    f_tax = ui.input("統一編號", value=vendor.tax_id if vendor else "")
                    f_terms = ui.number(
                        "月結天數（用於請款期限提醒，留空代表不提醒）",
                        value=vendor.payment_terms_days if vendor else None,
                    )
                    f_addr = ui.input("營業地址", value=vendor.address if vendor else "")

                    def save():
                        s2 = get_session()
                        try:
                            v = s2.query(Vendor).get(row["id"]) if row else Vendor(company_id=company_id)
                            v.vendor_code = f_code.value
                            v.vendor_name = f_name.value
                            v.contact_name = f_contact.value
                            v.contact_title = f_title.value
                            v.phone = f_phone.value
                            v.mobile = f_mobile.value
                            v.tax_id = f_tax.value
                            v.payment_terms_days = int(f_terms.value) if f_terms.value not in (None, "") else None
                            v.address = f_addr.value
                            if not row:
                                s2.add(v)
                            s2.commit()
                        finally:
                            s2.close()
                        dialog.close()
                        load(search.value)

                    with ui.row().classes("justify-end w-full gap-2 mt-2"):
                        ui.button("取消", on_click=dialog.close).props("flat")
                        ui.button("儲存", on_click=save)
                dialog.open()
            finally:
                session.close()

        table.on("edit-row", lambda e: open_edit_dialog(e.args))
        load()
