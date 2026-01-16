import re
from typing import Optional

def parse_money(val: Optional[str]) -> Optional[float]:
    if not val:
        return None

    s = (
        val.strip()
        .replace("R$", "")
        .replace("\u00a0", " ")
        .replace(" ", "")
    )

    s = re.sub(r"[^0-9,\.]", "", s)
    if not s:
        return None

    if s.count(",") > 1 and "." not in s:
        last = s.rfind(",")
        s = s[:last].replace(",", "") + "." + s[last + 1 :]
    elif s.count(".") > 1 and "," not in s:
        last = s.rfind(".")
        s = s[:last].replace(".", "") + "." + s[last + 1 :]
    else:
        if "," in s and "." in s:
            if s.rfind(",") > s.rfind("."):
                s = s.replace(".", "")
                s = s.replace(",", ".")
            else:
                s = s.replace(",", "")
        elif "," in s:
            s = s.replace(".", "")
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")

    try:
        value = float(s)
    except ValueError:
        return None

    return value if value > 0 else None

def extract_valor_total(source_text: str) -> Optional[float]:
    text = re.sub(r"\s+", " ", source_text)

    anchor = re.search(r"VALOR\s+TOTAL\s+DA\s+NOTA", text, re.IGNORECASE)
    if not anchor:
        return None

    window = text[anchor.end() : anchor.end() + 260]

    m = re.search(
        r"R?\$?\s*"
        r"([0-9]{1,3}(?:[.\s][0-9]{3})*|[0-9]{1,7})"
        r"(?:[,\.]\s*([0-9]{2}))",
        window,
    )
    if not m:
        return None

    integral = re.sub(r"\s+", "", m.group(1))
    cents = m.group(2)
    return parse_money(f"{integral},{cents}")
