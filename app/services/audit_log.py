# app/services/audit_log.py
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_audit_event(event: Dict[str, Any], path: str = "data/audit_nfse.jsonl") -> None:
    """
    Append-only audit log (JSONL). Cada linha = 1 evento JSON.
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    safe = dict(event)
    safe.setdefault("ts_utc", _utc_now_iso())

    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(safe, ensure_ascii=False) + "\n")
