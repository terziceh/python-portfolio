# invoice_db.py
# SQLite schema + init helpers for local invoice extraction

from datetime import datetime
import os
import sqlalchemy as sa
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, LargeBinary, DateTime, Float, ForeignKey, Text

Base = declarative_base()


class InvoiceRaw(Base):
    __tablename__ = "invoices_raw"
    id = Column(Integer, primary_key=True)
    filename = Column(String, nullable=False)
    mime = Column(String, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    file_bytes = Column(LargeBinary, nullable=False)


class InvoiceStaging(Base):
    __tablename__ = "invoices_staging"
    id = Column(Integer, primary_key=True)
    raw_id = Column(Integer, ForeignKey("invoices_raw.id"), nullable=False)

    # Core
    vendor = Column(String)
    invoice_date = Column(String)  # ISO date string
    total = Column(Float)

    # Utility fields
    account_number = Column(String)
    bill_date = Column(String)      # ISO
    due_date = Column(String)       # ISO
    service_from = Column(String)   # ISO
    service_to = Column(String)     # ISO
    usage_kwh = Column(Integer)
    total_current_charges = Column(Float)
    total_amount_due = Column(Float)

    # Diagnostics
    json_payload = Column(Text)     # raw JSON returned by Gemini
    status = Column(String, default="pending")
    validation_errors = Column(Text, nullable=True)


def init_db(db_path: str):
    """
    Creates outputs folder if needed, initializes SQLite + tables,
    returns (engine, SessionLocal).
    """
    out_dir = os.path.dirname(db_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    engine = sa.create_engine(f"sqlite:///{db_path}", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)
    return engine, SessionLocal
