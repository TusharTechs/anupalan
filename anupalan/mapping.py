"""Map an obligation to the government and department most likely responsible.

Keyword rules over the direction, the respondents and the order text. Output is a
suggestion with the evidence used; a legal officer confirms or changes it.
"""
from __future__ import annotations

import re

DEPARTMENTS = [
    ("School Education", r"school\s+education|D\.?G\.?S\.?E|DPI\b|teacher|master\s+cadre|lecturer|headmaster|principal,?\s+govt"),
    ("Higher Education", r"higher\s+education|college|university|professor|assistant\s+professor"),
    ("Health & Family Welfare", r"health|medical\s+officer|civil\s+surgeon|hospital|nurse|ANM\b|pharmacist|dental"),
    ("Police / Home", r"police|D\.?G\.?P\b|S\.?S\.?P\b|superintendent\s+of\s+police|home\s+department|constable|inspector\b|jail|prisons"),
    ("Finance / Pensions", r"finance\s+department|accountant\s+general|treasury|pension|DA\b|D\.?A\./D\.?R|dearness"),
    ("Revenue & Disaster Mgmt", r"revenue|deputy\s+commissioner|tehsildar|land\s+acquisition|collector|mutation|patwari"),
    ("Power (PSPCL / Nigams)", r"PSPCL|power(?:com)?\b|electricity|DHBVN|UHBVN|HVPNL|bijli|nigam"),
    ("Rural Development & Panchayats", r"panchayat|rural\s+development|BDPO|block\s+development|zila\s+parishad|MGNREGA"),
    ("Local Government / Urban", r"municipal|nagar|local\s+government|improvement\s+trust|urban\s+(?:development|estates)|HSVP|PUDA|GMADA|HUDA"),
    ("Irrigation / Water Resources", r"irrigation|water\s+resources|canal|public\s+health\s+engineering|water\s+supply"),
    ("Transport", r"transport|roadways|PRTC|PEPSU|state\s+transport|bus\s+stand"),
    ("Agriculture & Cooperation", r"agricultur|horticultur|cooperative|co-operative|mandi|markfed|hafed|marketing\s+board"),
    ("Forests & Environment", r"forest|wildlife|pollution\s+control|environment"),
    ("Social Justice & Welfare", r"social\s+(?:justice|security|welfare)|women\s+and\s+child|anganwadi|scheduled\s+caste|backward\s+class"),
    ("Defence (Union)", r"army|chief\s+of\s+(?:the\s+)?army|defence|armed\s+forces|PCDA|military|air\s+force|navy"),
    ("Recruitment Commissions (HPSC/HSSC/PPSC/PSSSB)", r"public\s+service\s+commission|staff\s+selection|subordinate\s+services\s+selection|HPSC|HSSC|PPSC|PSSSB|recruitment\s+board"),
    ("Personnel / General Admin", r"personnel|general\s+administration|chief\s+secretary|services\s+department|vigilance"),
]


def suggest(direction: str, respondents: str | None, order_text: str, governments: list[str]) -> dict:
    gov = governments[0] if governments else "Unspecified government"
    for scope_name, scope in (("direction", direction), ("respondents", respondents or ""), ("order", order_text[:4000])):
        for dept, pat in DEPARTMENTS:
            m = re.search(pat, scope, re.I)
            if m:
                return {"government": gov, "department": dept,
                        "evidence": f'"{m.group(0)}" in {scope_name}', "confidence": {"direction": 0.85, "respondents": 0.75, "order": 0.55}[scope_name]}
    return {"government": gov, "department": "To be assigned", "evidence": "no department keyword found", "confidence": 0.2}
