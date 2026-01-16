import io
from typing import Tuple
import pdfplumber

def extract_text_with_pdfplumber(pdf_bytes: bytes) -> Tuple[int, str]:
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        pages = len(pdf.pages)
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    return pages, text.strip()
