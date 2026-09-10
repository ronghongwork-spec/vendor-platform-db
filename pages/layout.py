import os
from nicegui import ui, app
from database import get_session
from models import Company

# 部署/測試期間可以先跳過登入，等一切設定好之後，把 Render 的環境變數 REQUIRE_LOGIN 改成 true（或直接刪掉這個變數）即可恢復要求登入
REQUIRE_LOGIN = os.getenv("REQUIRE_LOGIN", "false").lower() == "true"

COMPANIES = [
    ("xingsheng", "興聖"),
    ("ronghong", "容鴻"),
    ("fulaibo", "芙萊柏"),
    ("haitao", "海濤客"),
]

MODULES = [
    ("dashboard", "儀表板", "space_dashboard"),
    ("vendors", "廠商資料", "storefront"),
    ("payables", "應付帳款", "receipt_long"),
    ("expenses", "其他支出", "payments"),
    ("payments", "付款明細", "account_balance_wallet"),
    ("reminders", "請款期限提醒", "notifications_active"),
    ("import_data", "匯入資料", "upload_file"),
]


def require_login():
    """放在每個頁面最前面，沒登入就導去 /login（REQUIRE_LOGIN=false 時暫時跳過，供部署設定期間使用）"""
    if not REQUIRE_LOGIN:
        return True
    if not app.storage.user.get("authenticated"):
        ui.navigate.to("/login")
        return False
    return True


def get_company_id(company_code: str) -> int:
    session = get_session()
    try:
        c = session.query(Company).filter_by(code=company_code).first()
        return c.id if c else None
    finally:
        session.close()


def get_company_name(company_code: str) -> str:
    for code, name in COMPANIES:
        if code == company_code:
            return name
    return company_code


def header(active_company: str, active_module: str):
    """畫面最上方：左邊放公司切換 tabs，右邊放模組導覽 + 登出"""
    with ui.header().classes("items-center justify-between bg-neutral-800"):
        with ui.row().classes("items-center gap-1"):
            ui.label("集團財務追蹤平台").classes("text-lg font-bold mr-4")
            for code, name in COMPANIES:
                is_active = code == active_company
                ui.button(
                    name,
                    on_click=lambda c=code: ui.navigate.to(f"/c/{c}/{active_module}"),
                ).props("flat" if not is_active else "unelevated").classes(
                    "text-white" + (" bg-primary" if is_active else "")
                )
        with ui.row().classes("items-center gap-2"):
            display_name = app.storage.user.get("display_name")
            if REQUIRE_LOGIN or display_name:
                ui.label(f"登入者：{display_name or ''}").classes("text-white text-sm")
                ui.button(icon="logout", on_click=_logout).props("flat round").classes("text-white")
            else:
                ui.label("（測試模式：尚未啟用登入）").classes("text-white text-sm opacity-70")

    with ui.row().classes("w-full bg-neutral-100 px-4 py-1 gap-1"):
        for mod_code, mod_name, icon in MODULES:
            is_active = mod_code == active_module
            ui.button(
                mod_name,
                icon=icon,
                on_click=lambda m=mod_code: ui.navigate.to(f"/c/{active_company}/{m}"),
            ).props("flat" if not is_active else "unelevated").classes(
                "text-sm" + (" bg-primary text-white" if is_active else "")
            )


def _logout():
    app.storage.user.clear()
    ui.navigate.to("/login")
