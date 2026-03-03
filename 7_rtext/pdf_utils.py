"""
PDF reading utilities for tariff documents.
Uses pdfplumber when available for proper text extraction; otherwise falls back to raw decode.
"""

import base64
from pathlib import Path

try:
    import pdfplumber
    _HAS_PDFPLUMBER = True
except ImportError:
    _HAS_PDFPLUMBER = False


def read_pdf_as_text(pdf_path: str) -> str:
    """
    Read PDF and return extracted text (all pages).
    Uses pdfplumber when available so the full rate sheet is returned; otherwise
    decodes raw bytes (often gives junk for binary PDFs).
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if _HAS_PDFPLUMBER:
        with pdfplumber.open(path) as pdf:
            parts = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    parts.append(text)
            return "\n\n".join(parts) if parts else ""

    # Fallback: raw decode (binary PDFs become long garbage strings)
    content = path.read_bytes()
    return content.decode("utf-8", errors="ignore")


def encode_pdf_as_base64(pdf_path: str) -> str:
    """Encode PDF as base64 for vision API (future use)."""
    path = Path(pdf_path)
    return base64.b64encode(path.read_bytes()).decode("utf-8")
