"""
資料庫連線設定
- 正式環境：DATABASE_URL 指向 PostgreSQL（例如 Render 提供的免費 Postgres）
- 本機開發：沒設定 DATABASE_URL 時，自動退回本地 sqlite 檔案，方便先跑起來測試
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
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
    """建立所有資料表（存在的話不會動）+ 塞入四間公司基本資料與示範帳號"""
    import models  # noqa: F401  (確保 model 有被註冊到 Base.metadata)
    Base.metadata.create_all(engine)
    _seed_companies()


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
