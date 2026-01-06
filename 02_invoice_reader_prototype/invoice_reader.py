# invoice_reader.py
# Local runner:
# - Reads all PDFs from data/ and data/invoices/ (both supported)
# - Converts to images
# - Extracts structured JSON with Gemini
# - Writes to SQLite + exports CSV outputs you can open easily

import os
import json
from pathlib import Path

import pandas as pd
import sqlalchemy as sa
from dotenv import load_dotenv

from invoice_db import init_db, InvoiceRaw, InvoiceStaging
from gemini_extract import pdf_bytes_to_images, gemini_extract_from_images, validate_row


def main():
    # Load environment variables from .env (local only; do not commit)
    load_dotenv()

    base_dir = Path(__file__).resolve().parent

    # ✅ Support BOTH locations:
    # - data/*.pdf  (your current setup)
    # - data/invoices/*.pdf (cleaner structure if you move later)
    data_dir = base_dir / "data"
    invoices_subdir = data_dir / "invoices"

    outputs_dir = base_dir / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    # DB path in outputs (should be gitignored)
    db_path = str(outputs_dir / "invoices.sqlite")
    engine, SessionLocal = init_db(db_path)

    poppler_path = os.getenv("POPPLER_PATH")  # often needed on Windows

    # ✅ Gather PDFs from both paths, de-dupe, stable sort
    pdfs = []
    if data_dir.exists():
        pdfs += list(data_dir.glob("*.pdf"))
    if invoices_subdir.exists():
        pdfs += list(invoices_subdir.glob("*.pdf"))

    pdfs = sorted({p.resolve() for p in pdfs})  # de-dupe by absolute path

    if not pdfs:
        raise FileNotFoundError(
            f"No PDFs found. Looked in:\n- {data_dir}\n- {invoices_subdir}"
        )

    processed = 0
    failed = 0

    # Process PDFs -> DB
    with SessionLocal() as s:
        for pdf_path in pdfs:
            try:
                file_bytes = pdf_path.read_bytes()

                raw = InvoiceRaw(
                    filename=pdf_path.name,
                    mime="application/pdf",
                    file_bytes=file_bytes
                )
                s.add(raw)
                s.flush()

                images = pdf_bytes_to_images(file_bytes, dpi=300, poppler_path=poppler_path)
                data, raw_json = gemini_extract_from_images(images)

                st = InvoiceStaging(
                    raw_id=raw.id,
                    vendor=data.get("vendor"),
                    invoice_date=data.get("invoice_date"),
                    total=data.get("total"),

                    account_number=data.get("account_number"),
                    bill_date=data.get("bill_date") or data.get("invoice_date"),
                    due_date=data.get("due_date"),
                    service_from=data.get("service_from"),
                    service_to=data.get("service_to"),
                    usage_kwh=data.get("usage_kwh"),
                    total_current_charges=data.get("total_current_charges"),
                    total_amount_due=data.get("total_amount_due") or data.get("total"),

                    # keep the raw JSON text for auditing
                    json_payload=raw_json if isinstance(raw_json, str) else json.dumps(raw_json),
                    status="pending"
                )

                errs = validate_row({**data})
                if errs:
                    st.validation_errors = json.dumps(errs)

                s.add(st)
                processed += 1
                print(f"✅ Extracted: {pdf_path.name}")

            except Exception as e:
                failed += 1
                print(f"❌ Failed: {pdf_path.name} — {e}")

        s.commit()

    # Export CSVs (easy to open in VS Code / Excel)
    with engine.connect() as conn:
        staging_df = pd.read_sql(sa.text("SELECT * FROM invoices_staging"), conn)
        raw_df = pd.read_sql(sa.text("SELECT id, filename, uploaded_at FROM invoices_raw"), conn)

    # Full exports
    staging_csv = outputs_dir / "invoices_staging.csv"
    raw_csv = outputs_dir / "invoices_raw.csv"
    staging_df.to_csv(staging_csv, index=False)
    raw_df.to_csv(raw_csv, index=False)

    # Pretty export (most useful columns)
    pretty_cols = [
        "id", "raw_id", "vendor", "account_number",
        "bill_date", "due_date", "service_from", "service_to",
        "usage_kwh", "total_current_charges", "total_amount_due",
        "invoice_date", "total", "status", "validation_errors"
    ]
    pretty_cols = [c for c in pretty_cols if c in staging_df.columns]
    pretty_csv = outputs_dir / "invoices_staging_pretty.csv"
    staging_df[pretty_cols].to_csv(pretty_csv, index=False)

    # Timestamped copy (nice for tracking runs)
    run_csv = outputs_dir / f"invoices_staging_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
    staging_df.to_csv(run_csv, index=False)

    print("\n--- Run Summary ---")
    print(f"Processed: {processed}")
    print(f"Failed:    {failed}")
    print(f"DB:        {db_path}")
    print("CSV exports:")
    print(f" - {staging_csv}")
    print(f" - {pretty_csv}")
    print(f" - {raw_csv}")
    print(f" - {run_csv}")


if __name__ == "__main__":
    main()
