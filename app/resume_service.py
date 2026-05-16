"""Extract text from resume PDF bytes (not stored on disk)."""
from io import BytesIO

from pypdf import PdfReader


def extract_pdf_bytes(data: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(data))
        parts = []
        for page in reader.pages:
            text = page.extract_text() or ""
            if text.strip():
                parts.append(text)
        return "\n".join(parts).strip()
    except Exception:  # noqa: BLE001
        return ""
