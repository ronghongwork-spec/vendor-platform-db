import tempfile
import os
from nicegui import ui, app
from database import get_session
from models import ImportBatch
from pages.layout import header, require_login, get_company_id
from importers.vendor_importer import import_vendors
from importers.payable_importer import import_payables
from importers.expense_importer import import_expenses
from importers.payment_importer import import_payments

MODULE_MAP = {
    "廠商資料": ("vendor", import_vendors, "廠商資料20260909152211.xlsx 這類檔案，欄位含序號/廠商代號/廠商簡稱/統一編號等"),
    "應付帳款明細": ("payable", import_payables, "應付帳款明細表20260909151628.xlsx 這類檔案，會整批覆蓋此公司舊資料"),
    "其他支出明細": ("expense", import_expenses, "其他支出明細表20260909152032.xlsx 這類檔案，會整批覆蓋此公司舊資料"),
    "付款明細": ("payment", import_payments, "付款明細表20260909151657.xlsx 這類檔案，會整批覆蓋此公司舊資料"),
}


def render(company_code: str):
    if not require_login():
        return
    company_id = get_company_id(company_code)
    header(company_code, "import_data")

    with ui.column().classes("w-full p-6 gap-6"):
        ui.label("匯入資料").classes("text-2xl font-bold")
        ui.label("請從鼎新A1匯出對應的 Excel 報表後，在下方對應區塊上傳。").classes("text-sm text-gray-500")

        for label, (module, importer_fn, hint) in MODULE_MAP.items():
            with ui.card().classes("w-full"):
                ui.label(label).classes("text-lg font-bold")
                ui.label(hint).classes("text-xs text-gray-400")

                def make_handler(importer_fn=importer_fn, module=module, label=label):
                    def handle_upload(e):
                        suffix = os.path.splitext(e.name)[1] or ".xlsx"
                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                            tmp.write(e.content.read())
                            tmp_path = tmp.name
                        try:
                            username = app.storage.user.get("username", "unknown")
                            result = importer_fn(tmp_path, company_id, e.name, username)
                            ui.notify(f"{label} 匯入成功：{result}", type="positive")
                            refresh_log()
                        except Exception as ex:
                            ui.notify(f"{label} 匯入失敗：{ex}", type="negative")
                        finally:
                            os.unlink(tmp_path)
                    return handle_upload

                ui.upload(on_upload=make_handler(), auto_upload=True).props("accept=.xlsx").classes("w-full")

        ui.separator()
        ui.label("最近匯入紀錄").classes("text-lg font-bold")
        log_table = ui.table(
            columns=[
                {"name": "module", "label": "模組", "field": "module", "align": "left"},
                {"name": "filename", "label": "檔名", "field": "filename", "align": "left"},
                {"name": "imported_by", "label": "匯入者", "field": "imported_by", "align": "left"},
                {"name": "imported_at", "label": "時間", "field": "imported_at", "align": "left"},
                {"name": "row_count", "label": "筆數", "field": "row_count", "align": "right"},
            ],
            rows=[],
            row_key="id",
        ).classes("w-full").props("dense flat bordered")

        def refresh_log():
            session = get_session()
            try:
                batches = session.query(ImportBatch).filter(ImportBatch.company_id == company_id) \
                    .order_by(ImportBatch.imported_at.desc()).limit(20).all()
                log_table.rows = [{
                    "id": b.id, "module": b.module, "filename": b.filename,
                    "imported_by": b.imported_by,
                    "imported_at": b.imported_at.strftime("%Y-%m-%d %H:%M") if b.imported_at else "",
                    "row_count": b.row_count,
                } for b in batches]
                log_table.update()
            finally:
                session.close()

        refresh_log()
