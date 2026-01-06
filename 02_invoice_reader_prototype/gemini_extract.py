# gemini_extract.py
# PDF -> images -> Gemini multimodal extraction (strict JSON) + normalization

from __future__ import annotations

from datetime import date
from dateutil.parser import parse as parse_date
import io
import json
import os
import re
from typing import List, Optional, Tuple

from pdf2image import convert_from_bytes
from PIL import Image
import google.generativeai as genai


MODEL_ID = os.getenv("GEMINI_MODEL_ID", "models/gemini-2.5-flash")

GEMINI_PROMPT = (
    "You are a strict invoice extractor. Read the utility bill IMAGES and return ONLY JSON "
    "with these keys (null if unknown): "
    "vendor, invoice_date (YYYY-MM-DD), total, "
    "account_number, bill_date (YYYY-MM-DD), due_date (YYYY-MM-DD), "
    "service_from (YYYY-MM-DD), service_to (YYYY-MM-DD), usage_kwh (integer), "
    "total_current_charges, total_amount_due. "
    "No prose, no markdown—JSON only."
)


def _pil_to_jpeg_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def pdf_bytes_to_images(file_bytes: bytes, dpi: int = 300, poppler_path: Optional[str] = None) -> List[Image.Image]:
    """
    Convert PDF bytes to list of PIL Images. On Windows, poppler_path may be required.
    """
    try:
        return convert_from_bytes(file_bytes, dpi=dpi, poppler_path=poppler_path)
    except Exception:
        # fallback: try open as image (if user passed jpg/png bytes)
        try:
            img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
            return [img]
        except Exception:
            return []


def to_iso(d: Optional[str], fallback_year: Optional[int] = None) -> Optional[str]:
    if not d:
        return None
    try:
        return parse_date(str(d), dayfirst=False).date().isoformat()
    except Exception:
        pass

    # handle "MM/DD" with a fallback year
    m = re.match(r"^\s*(\d{1,2})/(\d{1,2})\s*$", str(d))
    if m and fallback_year:
        try:
            return date(int(fallback_year), int(m.group(1)), int(m.group(2))).isoformat()
        except Exception:
            return None
    return None


def num(x) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)

    s = str(x).replace(",", "").replace("$", "").strip()
    s = s.replace("O", "0").replace("o", "0").replace("S", "5")  # light OCR-like cleanup
    try:
        return float(s)
    except Exception:
        return None


def validate_row(d: dict) -> List[str]:
    errs = []
    if not (d.get("account_number") and d.get("invoice_date")):
        errs.append("Missing (account_number + invoice_date)")
    if d.get("invoice_date"):
        try:
            _ = parse_date(d["invoice_date"]).date()
        except Exception:
            errs.append("Invalid invoice_date")
    return errs


def gemini_extract_from_images(page_images: List[Image.Image]) -> Tuple[dict, str]:
    """
    Send images to Gemini with forced JSON output. Returns (normalized_data, raw_json_text).
    Raises if GEMINI_API_KEY is missing or response can't be parsed.
    """
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set. Put it in your environment or .env file.")

    genai.configure(api_key=key)

    if not page_images:
        raise RuntimeError("No page images to send to Gemini.")

    parts = [GEMINI_PROMPT]
    for img in page_images:
        parts.append({"mime_type": "image/jpeg", "data": _pil_to_jpeg_bytes(img)})

    model = genai.GenerativeModel(
        model_name=MODEL_ID,
        generation_config={"response_mime_type": "application/json"}
    )

    resp = model.generate_content(parts)
    raw = (resp.text or "").strip()

    data = json.loads(raw)

    # normalize dates
    for k in ["invoice_date", "bill_date", "due_date", "service_from", "service_to"]:
        if data.get(k):
            data[k] = to_iso(data[k])

    # normalize numeric money
    for k in ["total_current_charges", "total_amount_due", "total"]:
        data[k] = num(data.get(k))

    # normalize usage
    if data.get("usage_kwh") is not None:
        try:
            data["usage_kwh"] = int(str(data["usage_kwh"]).replace(",", "").strip())
        except Exception:
            data["usage_kwh"] = None

    return data, raw
