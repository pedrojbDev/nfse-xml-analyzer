import re
from typing import Optional

def find_regex(pattern: str, source_text: str) -> Optional[str]:
    m = re.search(pattern, source_text, re.IGNORECASE | re.MULTILINE)
    return m.group(1).strip() if m else None
