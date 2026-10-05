"""Historical backtest: would Anupalan have flagged directions that later led to contempt?

1. Read contempt (COCP) orders; find the order they say was disobeyed
   ("non-compliance of the order dated 29.04.2024 passed in CWP-9594-2024").
2. Locate that original order in the open High Court dataset and run the pipeline on it.
3. Compare the extracted deadline with the date the contempt petition was filed.
"""
from __future__ import annotations

import re
from datetime import date

from .meta import parse_date

REF = re.compile(
    r"(?:order|judgment|directions?)\s*(?:\(s\)\s*)?dated\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})"
    r"(?:\s*\(Annexure\s*P-?\d+\))?[^.]{0,120}?\bin\s+(CWP|LPA|RSA|CM|CR|CWP-PIL|FAO)[\s\-.]*(?:No\.?\s*)?(\d{1,6})[\s\-/]*(?:of\s+)?(\d{4})",
    re.I | re.S,
)


def find_reference(text: str):
    t = re.sub(r"\s+", " ", text)
    m = REF.search(t)
    if not m:
        return None
    d = parse_date(m.group(1))
    return {"order_date": d, "case_type": m.group(2).upper(), "case_no": int(m.group(3)), "case_year": int(m.group(4)),
            "evidence": m.group(0)[:400]}
