"""Rule-based detection of operative directions to government.

Finds sentences that create an obligation for a respondent authority, skipping
counsel's submissions, liberty clauses and bare dismissals. Each hit keeps its
exact character span so the reviewer can see the source text.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

ABBREV = {"no", "nos", "dr", "mr", "mrs", "ms", "sh", "smt", "hon'ble", "addl", "sr", "jr", "govt", "dept", "vs",
          "viz", "i.e", "e.g", "ld", "adv", "st", "co", "ltd", "annex", "w.e.f", "w.r.t", "s", "art", "rs", "v", "prof", "u.t", "p"}
BOUNDARY = re.compile(r"[.;]\s+(?=[A-Z0-9(\[\"'])")

DIRECTIVE = re.compile(
    r"\b(?:(?:is|are|be|stand|stands|hereby)\s+(?:hereby\s+)?directed"
    r"|direct(?:ed)?\s+the\s+(?:respondent|state|competent|authorit|concerned)"
    r"|(?:respondents?|state|authorit(?:y|ies)|competent\s+authority|department|board|corporation|university)[^.;]{0,140}?\bshall\b"
    r"|\b(?:the\s+same|it|the\s+claim|the\s+representation|the\s+case|the\s+matter|the\s+amount|the\s+benefits?|the\s+arrears?)\s+(?:shall\s+)?be\s+(?:decided|considered|re-?considered|released|paid|disbursed|granted|examined|processed|finali[sz]ed|settled|passed|implemented|complied)"
    r"|\bdirection\s+(?:is|are)\s+issued|\bmandamus\b"
    r"|\bwith\s+a\s+direction\s+to\b|\bdirection\s+to\s+(?:the\s+)?(?:respondent|competent|state|authorit|concerned|deputy|director|secretary|commissioner)"
    r"|\blet\s+the\s+needful\s+be\s+done\b"
    r"|\bis\s+directed\s+to\s+be\s+(?:decided|considered|released|paid)"
    r"|\bto\s+(?:decide|consider|release|pay|pass)\b[^.;]{0,60}\bwithin\b)",
    re.I,
)
SUBMISSION = re.compile(r"\b(?:submits?|submitted|contends?|contended|prays?|prayed|argues?|argued|states?\s+that|seeks?|sought|has\s+urged|it\s+is\s+pointed\s+out|learned\s+counsel)\b", re.I)
LIBERTY = re.compile(r"\bliberty\b|\bfree\s+to\b|\bopen\s+to\s+the\s+petitioner", re.I)
NOT_GOVT = re.compile(r"\b(?:registry|office|the\s+counsel|learned\s+counsel|petitioner)\s+(?:is|are|shall|be)\s+(?:also\s+)?directed|\blist\s+(?:the\s+case|on|again|for)|\bissue\s+notice|\badjourn|\btag\s+(?:the\s+same|with)|\bplace\s+(?:a\s+)?copy|\bcopy\s+of\s+this\s+order\s+be\s+placed|\bnext\s+date\s+of\s+hearing", re.I)
PRAYER = re.compile(r"petition\s+(?:has\s+been|is)\s+filed|in\s+the\s+nature\s+of|praying\s+for|seeking\s+(?:a\s+)?(?:writ|direction|issuance)|for\s+issuance\s+of|prayer\s+(?:is|made)", re.I)
STATUTE = re.compile(r"\bsub-rule\b|\bunder\s+these\s+rules\b|\bthis\s+Act\b|\bprovided\s+that\b|\bnotwithstanding\b", re.I)
NEGATIVE = re.compile(r"\bdismissed\b(?![^.]{0,60}direct)|\bnot\s+pressed\b(?![^.]{0,80}direct)|\bwithdrawn\b", re.I)

ACTION_TYPES = [
    ("Decide representation", r"representation|legal\s+notice|decide\s+the\s+claim|claim\s+of\s+the\s+petitioner"),
    ("Release payment / arrears", r"\b(?:release|pay|paid|disburse|arrears?|interest|dues|amount|salary|pension(?:ary)?\s+benefits|gratuity|leave\s+encashment|DA\b|DR\b)"),
    ("Grant service benefit", r"regulari[sz]|promot|seniority|pay\s+scale|increment|ACP|appoint|reinstat|benefit\s+of"),
    ("Reconsider / pass speaking order", r"reconsider|re-consider|speaking\s+order|reasoned\s+order|fresh\s+order|consider\s+the\s+case"),
    ("Conduct inquiry / action", r"inquiry|enquiry|investigat|action\s+against|FIR"),
    ("File report / affidavit", r"status\s+report|affidavit|compliance\s+report"),
]


@dataclass
class Direction:
    text: str
    start: int
    end: int
    action_type: str
    strength: float  # 0..1 rule confidence


def sentences(text: str):
    pos = 0
    for para in re.split(r"(\n\s*\n)", text):
        if not para.strip() or para.isspace():
            pos += len(para)
            continue
        last = 0
        for m in BOUNDARY.finditer(para):
            prev = re.search(r"([\w.'/]+)$", para[last:m.start()])
            if prev and (prev.group(1).lower() in ABBREV or re.fullmatch(r"\d{1,2}", prev.group(1))):
                continue  # "No. 2", "Dr.", dates like 22.07.2025 handled by requiring whitespace
            yield para[last:m.start() + 1], pos + last
            last = m.end()
        yield para[last:], pos + last
        pos += len(para)


def classify(s: str) -> str:
    for name, pat in ACTION_TYPES:
        if re.search(pat, s, re.I):
            return name
    return "Other direction"


def find(text: str) -> list[Direction]:
    out: list[Direction] = []
    n = len(text)
    for s, start in sentences(text):
        st = s.strip()
        if len(st) < 25 or not DIRECTIVE.search(st):
            continue
        if NOT_GOVT.search(st) or PRAYER.search(st):
            continue
        if STATUTE.search(st) and not re.search(r"\b(?:is|are|be)\s+directed\b", st, re.I):
            continue
        strength = 0.6
        if SUBMISSION.search(st):
            if re.search(r"\bmay\s+be\s+directed|\bprays?\b|\bseeks?\b|\bsubmits?\b", st, re.I):
                continue  # counsel asking for a direction, not the court giving it
            strength -= 0.25
        if LIBERTY.search(st) and not re.search(r"\b(?:shall|be\s+decided|directed)\b", st, re.I):
            continue
        if NEGATIVE.search(st) and not re.search(r"direct", st, re.I):
            continue
        if re.search(r"\bwithin\b", st, re.I):
            strength += 0.2
        if start > n * 0.45:
            strength += 0.1   # operative portion is usually at the end
        lead = len(s) - len(s.lstrip())
        out.append(Direction(st, start + lead, start + lead + len(st), classify(st), round(min(strength, 1.0), 2)))
    return out


REFERENCE = re.compile(
    r"(?:disposed\s+of\s+in\s+terms\s+of|for\s+(?:the\s+)?orders?,?\s+see|governed\s+by|covered\s+by)[^.]{0,80}?"
    r"(?:order|judgment)?[^.]{0,40}?\b(CWP|LPA|RSA|CWP-PIL)[\s\-.]*(?:No\.?\s*)?(\d{1,6})[\s\-/]*(?:of\s+)?(\d{4})"
    r"(?:[^.]{0,160}?(?:on|dated|decided\s+on)\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4}))?",
    re.I,
)


def find_references(text: str) -> list[dict]:
    """Orders that only say 'disposed of in terms of the order in CWP-X': the obligation lives in another judgment."""
    out = []
    for m in REFERENCE.finditer(text):
        out.append({"text": m.group(0), "start": m.start(), "end": m.end(),
                    "ref_case": f"{m.group(1).upper()}-{m.group(2)}-{m.group(3)}", "ref_date": m.group(4)})
    return out
