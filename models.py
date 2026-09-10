from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, Boolean,
    ForeignKey, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship
from database import Base


class Company(Base):
    """四間分公司：興聖 / 容鴻 / 芙萊柏 / 海濤客"""
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)   # xingsheng / ronghong / fulaibo / haitao
    name = Column(String(100), nullable=False)

    vendors = relationship("Vendor", back_populates="company")


class User(Base):
    """內部登入帳號（僅公司內部人員使用，不對廠商開放）"""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ImportBatch(Base):
    """每次匯入 Excel 的紀錄，方便追蹤是誰、何時、匯入哪個模組的哪個檔案"""
    __tablename__ = "import_batches"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    module = Column(String(20), nullable=False)   # vendor / payable / expense / payment
    filename = Column(String(255))
    imported_by = Column(String(50))
    imported_at = Column(DateTime, default=datetime.utcnow)
    row_count = Column(Integer, default=0)


class Vendor(Base):
    """廠商資料主檔"""
    __tablename__ = "vendors"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    seq_no = Column(String(20))            # 序號
    vendor_code = Column(String(50), index=True)      # 廠商代號
    vendor_name = Column(String(200), index=True)     # 廠商簡稱
    full_name = Column(String(200))        # 廠商全名
    phone = Column(String(50))
    fax = Column(String(50))
    contact_name = Column(String(50))
    contact_title = Column(String(50))
    mobile = Column(String(50))
    email = Column(String(100))
    address = Column(String(255))          # 營業地址
    billing_address = Column(String(255))  # 帳單地址
    tax_id = Column(String(20), index=True)           # 統一編號
    remit_account = Column(String(50))                # 匯款帳號
    remark = Column(Text)                  # 備註

    # 結帳/付款規則（來自廠商資料 Excel，全部分公司共用同一套欄位定義）
    settlement_method = Column(String(20))       # 結帳方式：月結 / 貨到
    delivery_days = Column(Integer)              # 貨到天數（結帳方式=貨到 時使用）
    settlement_day = Column(Integer)             # 每月結帳日（1~31，31代表月底）
    settlement_month_offset = Column(String(20)) # 月結月：本月 / 下1個月
    payment_calc_method = Column(String(20))     # 付款日計算方式：每月付款日 / 付款天數
    payment_days = Column(Integer)               # 付款天數（付款日計算方式=付款天數 時使用）
    settlement_day_label = Column(String(20))    # 月結日（Excel原始文字，僅供顯示參考）
    payment_day_label = Column(String(20))       # 付款日（Excel原始文字，僅供顯示參考）

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="vendors")

    __table_args__ = (
        UniqueConstraint("company_id", "vendor_code", name="uq_vendor_company_code"),
    )


class Payable(Base):
    """應付帳款明細（每次匯入視為該公司當下最新快照，會整批覆蓋舊資料）"""
    __tablename__ = "payables"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    import_batch_id = Column(Integer, ForeignKey("import_batches.id"))

    vendor_name_raw = Column(String(200), index=True)   # 廠商（原始文字，不一定能對到 vendor_code）
    vendor_id = Column(Integer, ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True)

    doc_date = Column(Date)          # 單據日期
    source_no = Column(String(50), index=True)   # 來源單號
    handler = Column(String(50))     # 經辦人
    invoice_no = Column(String(50), index=True)  # 發票號碼
    item_no = Column(String(50))     # 品號
    item_name = Column(String(200))  # 品名
    qty = Column(Float)
    unit = Column(String(20))
    unit_price = Column(Float)
    amount = Column(Float)
    remit_account = Column(String(50))  # 匯款帳號


class OtherExpense(Base):
    """其他支出明細（雜費、營業外支出等；每次匯入整批覆蓋舊資料）"""
    __tablename__ = "other_expenses"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    import_batch_id = Column(Integer, ForeignKey("import_batches.id"))

    reason = Column(String(200))       # 原因
    doc_date = Column(Date)            # 日期
    doc_no = Column(String(50), index=True)  # 單據
    target_name = Column(String(200), index=True)  # 客戶/廠商
    amount_untaxed = Column(Float)     # 未稅金額
    tax_amount = Column(Float)         # 稅額
    total_amount = Column(Float)       # 總金額
    summary = Column(Text)             # 摘要

    # Excel 沒有明確的付款狀態欄位，先用人工可勾選的欄位管理，預設未付款
    is_paid = Column(Boolean, default=False)


class Payment(Base):
    """付款明細（實際撥款/沖帳紀錄；每次匯入整批覆蓋舊資料）"""
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    import_batch_id = Column(Integer, ForeignKey("import_batches.id"))

    vendor_name_raw = Column(String(200), index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True)

    payment_date = Column(Date)       # 付款日期
    payment_no = Column(String(50), index=True)  # 付款單號
    payer = Column(String(50))        # 付款人
    cash_amt = Column(Float, default=0)      # 現金
    transfer_amt = Column(Float, default=0)  # 轉帳
    check_amt = Column(Float, default=0)     # 支票
    other_amt = Column(Float, default=0)     # 其他
    other_note = Column(String(200))         # 其他說明
    total_amt = Column(Float, default=0)     # 付款合計
    discount_amt = Column(Float, default=0)  # 折讓
    counter_account = Column(String(50))     # 對方帳號
