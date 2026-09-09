"""
建立內部登入帳號用的小工具。
用法：
    python create_admin.py <帳號> <密碼> [顯示名稱]
範例：
    python create_admin.py finance 一組強密碼 財務部
"""
import sys
from database import init_db
from auth import create_user

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法：python create_admin.py <帳號> <密碼> [顯示名稱]")
        sys.exit(1)

    init_db()
    username = sys.argv[1]
    password = sys.argv[2]
    display_name = sys.argv[3] if len(sys.argv) > 3 else username

    create_user(username, password, display_name)
    print(f"已建立帳號：{username}")
