from nicegui import ui, app
from auth import verify_login
from database import get_session
from models import User


def render():
    with ui.column().classes("absolute-center items-center gap-4"):
        ui.label("集團財務追蹤平台").classes("text-2xl font-bold")
        ui.label("僅供內部人員登入使用").classes("text-sm text-gray-500")
        with ui.card().classes("w-80 p-6 gap-2"):
            username = ui.input("帳號").classes("w-full")
            password = ui.input("密碼", password=True, password_toggle_button=True).classes("w-full")
            error_label = ui.label().classes("text-red-500 text-sm")

            def do_login():
                if verify_login(username.value, password.value):
                    session = get_session()
                    try:
                        user = session.query(User).filter_by(username=username.value).first()
                        app.storage.user.update({
                            "authenticated": True,
                            "username": user.username,
                            "display_name": user.display_name,
                        })
                    finally:
                        session.close()
                    ui.navigate.to("/c/xingsheng/dashboard")
                else:
                    error_label.text = "帳號或密碼錯誤"

            password.on("keydown.enter", lambda: do_login())
            ui.button("登入", on_click=do_login).classes("w-full mt-2")
