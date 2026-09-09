import os
from nicegui import ui
from dotenv import load_dotenv

from database import init_db
from pages import login, dashboard, vendors, payables, expenses, payments, reminders, import_data

load_dotenv()

PAGE_RENDERERS = {
    "dashboard": dashboard.render,
    "vendors": vendors.render,
    "payables": payables.render,
    "expenses": expenses.render,
    "payments": payments.render,
    "reminders": reminders.render,
    "import_data": import_data.render,
}


@ui.page("/")
def index():
    ui.navigate.to("/c/xingsheng/dashboard")


@ui.page("/login")
def login_page():
    login.render()


@ui.page("/c/{company_code}/{module}")
def company_module_page(company_code: str, module: str):
    renderer = PAGE_RENDERERS.get(module)
    if not renderer:
        ui.label(f"找不到模組：{module}")
        return
    renderer(company_code)


init_db()

ui.run(
    title="集團財務追蹤平台",
    storage_secret=os.getenv("STORAGE_SECRET", "please-change-this-secret-in-production"),
    port=int(os.getenv("PORT", 8080)),
    host="0.0.0.0",
)
