from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Tuple

PDF_MAGIC = b"%PDF-"

@dataclass(frozen=True)
class PayloadInfo:
    filename: str
    content_type: str
    raw_bytes: bytes

    @property
    def size(self) -> int:
        return len(self.raw_bytes)

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.raw_bytes).hexdigest()

def normalize_pdf_payload(raw: bytes) -> Tuple[bytes, str, bool, str]:
    if raw.startswith(PDF_MAGIC):
        return raw, "none", True, raw[:8].decode("latin1", errors="replace")

    idx = raw.find(PDF_MAGIC)
    if idx != -1:
        header = raw[idx : idx + 8].decode("latin1", errors="replace")
        return raw[idx:], "cut_to_pdf_header", True, header

    return raw, "none", False, ""
