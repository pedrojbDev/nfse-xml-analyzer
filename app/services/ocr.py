import os
from typing import Optional, Tuple

import fitz  # pymupdf
import pytesseract
from PIL import Image

def configure_tesseract() -> None:
    cmd = os.getenv("TESSERACT_CMD")
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd

def ocr_pdf_with_tesseract(
    pdf_bytes: bytes,
    lang: str = "por+eng",
    config: str = "--oem 3 --psm 6",
    only_first_page: bool = False,
    crop_rect: Optional[Tuple[float, float, float, float]] = None,
) -> Tuple[int, str]:
    configure_tesseract()

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        texts: list[str] = []
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)

        pages_iter = [doc.load_page(0)] if only_first_page else list(doc)

        for page in pages_iter:
            if crop_rect:
                pix = page.get_pixmap(matrix=mat, clip=fitz.Rect(*crop_rect))
            else:
                pix = page.get_pixmap(matrix=mat)

            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            texts.append(pytesseract.image_to_string(img, lang=lang, config=config))

        return len(texts), "\n".join(texts).strip()
    finally:
        doc.close()
