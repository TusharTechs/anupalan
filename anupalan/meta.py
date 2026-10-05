"""Order header parsing: case number, decision date, parties, state, counsel."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from dateutil import parser as dparser

CASE_NO = re.compile(r"\b(CWP|COCP|CM|CRM-M|RSA|LPA|CR|CRR|CRA-S|CWP-PIL|FAO|W\.P\.\(C\)|CONT\.CAS\(C\))[\s\-/.]*(?:No\.?\s*)?(\d{1,6})[\s\-/]*(?:of\s+)?(\d{4})", re.I)
DECISION = re.compile(r"Date of (?:decision|order|pronouncement)\s*[:\-]?\s*([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4}|[A-Z][a-z]+\.?\s+\d{1,2},?\s+\d{4}|\d{1,2}(?:st|nd|rd|th)?\s+[A-Z][a-z]+,?\s+\d{4})", re.I)
STATES = {
    "Punjab": r"State of Punjab|Govt\.? of Punjab|Government of Punjab|A\.?G\.?,? Punjab|DAG,? Punjab|Punjab State",
    "Haryana": r"State of Haryana|Govt\.? of Haryana|Government of Haryana|A\.?G\.?,? Haryana|DAG,? Haryana|Haryana State",
    "UT Chandigarh": r"U\.?T\.?,? Chandigarh|Chandigarh Administration",
    "Union of India": r"Union of India|UOI\b|Central Government Standing Counsel|Sr\.? Panel Counsel",
    "Delhi (GNCTD)": r"GNCTD|Govt\.? of NCT of Delhi|Government of NCT of Delhi",
}


@dataclass
class OrderMeta:
    case_no: str | None = None
    case_type: str | None = None
    decision_date: date | None = None
    petitioner: str | None = None
    respondents: str | None = None
    governments: list[str] = field(default_factory=list)
    judge: str | None = None


def parse_date(s: str) -> date | None:
    try:
        return dparser.parse(s.replace(",", " "), dayfirst=True, fuzzy=True).date()
    except (ValueError, OverflowError):
        return None


def parse(text: str, title: str | None = None) -> OrderMeta:
    m = OrderMeta()
    head = text[:2500]
    cm = CASE_NO.search(title or "") or CASE_NO.search(head)
    if cm:
        m.case_type = cm.group(1).upper()
        m.case_no = f"{m.case_type}-{cm.group(2)}-{cm.group(3)}"
    dm = DECISION.search(head)
    if dm:
        m.decision_date = parse_date(dm.group(1))
    if title and " Vs " in title:
        left, right = title.split(" Vs ", 1)
        m.petitioner = re.sub(r"^.*? of ", "", left).strip().title()
        m.respondents = right.strip().title()
    else:
        pm = re.search(r"\n([^\n]{3,120}?)\s*\.{2,}\s*Petitioner", head)
        rm = re.search(r"Versus\s*\n([^\n]{3,160}?)\s*\.{2,}\s*Respondent", head, re.I)
        m.petitioner = pm.group(1).strip() if pm else None
        m.respondents = rm.group(1).strip() if rm else None
    scope = (title or "") + "\n" + head
    m.governments = [g for g, pat in STATES.items() if re.search(pat, scope, re.I)]
    jm = re.search(r"CORAM\s*:?\s*(HON'?BLE[^\n]+)", head, re.I)
    m.judge = jm.group(1).strip() if jm else None
    return m
