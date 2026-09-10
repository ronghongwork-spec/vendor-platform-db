"""
資料庫連線設定
- 正式環境：DATABASE_URL 指向 PostgreSQL（例如 Render 提供的免費 Postgres）
- 本機開發：沒設定 DATABASE_URL 時，自動退回本地 sqlite 檔案，方便先跑起來測試
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./local_dev.db")

# Render 給的 Postgres URL 有時是 postgres:// 開頭，SQLAlchemy 2.0 要 postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_session():
    return SessionLocal()


def init_db():
    """建立所有資料表（存在的話不會動）+ 自動補上程式改版後新增的欄位 + 塞入四間公司基本資料"""
    import models  # noqa: F401  (確保 model 有被註冊到 Base.metadata)
    Base.metadata.create_all(engine)
    _sync_missing_columns()
    _seed_companies()


def _sync_missing_columns():
    """
    輕量版 schema migration：比對資料庫現有欄位跟 models.py 定義的欄位，
    少什麼欄位就自動用 ALTER TABLE 補上（都補成允許 NULL，不會動到既有資料）。
    這樣以後只要在 models.py 加新欄位，重新部署就會自動生效，不用手動下 SQL。
    """
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table_name, table in Base.metadata.tables.items():
            if not inspector.has_table(table_name):
                continue  # 全新的表，create_all 已經建好完整欄位，不用補
            existing_columns = {c["name"] for c in inspector.get_columns(table_name)}
            for column in table.columns:
                if column.name in existing_columns:
                    continue
                col_type = column.type.compile(engine.dialect)
                conn.execute(text(f'ALTER TABLE {table_name} ADD COLUMN "{column.name}" {col_type}'))


def _seed_companies():
    from models import Company
    session = get_session()
    try:
        existing = {c.code for c in session.query(Company).all()}
        defaults = [
            ("xingsheng", "興聖國際(股)公司"),
            ("ronghong", "容鴻(股)公司"),
            ("fulaibo", "芙萊柏(股)公司"),
            ("haitao", "海濤客食品工業(股)公司"),
        ]
        for code, name in defaults:
            if code not in existing:
                session.add(Company(code=code, name=name))
        session.commit()
    finally:
        session.close()
