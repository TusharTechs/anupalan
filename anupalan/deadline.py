"""Deterministic deadline engine.

Turns Indian judicial time phrases ("within a fortnight", "within a further period
of 3 months from its receipt", "within six weeks from the date of receipt of a
certified copy") into a due date with an explicit basis. The LLM never computes
dates; this module does, so every date is reproducible and explainable.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

WORD_NUM = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "fifteen": 15, "twenty": 20, "thirty": 30, "forty": 40, "forty-five": 45,
    "sixty": 60, "ninety": 90,
}
NUM = r"(\d{1,3}|" + "|".join(sorted(WORD_NUM, key=len, reverse=True)) + r")"
UNIT = r"(days?|weeks?|months?|years?|fortnights?)"

# Default assumptions, surfaced to the reviewer whenever used.
CERTIFIED_COPY_DAYS = 7      # time for a certified copy / order to reach the department
REPRESENTATION_DAYS = 0      # if the petitioner must first file something and no window is given


@dataclass
class Deadline:
    phrase: str                       # exact text matched in the order
    due: date | None                  # latest date by which the action is due
    anchor: str                       # "order_date" | "receipt_of_copy" | "receipt_of_representation" | "none"
    certainty: str                    # "exact" | "assumed_anchor" | "conditional" | "open_ended"
    basis: str                        # plain-English explanation shown to reviewers
    assumptions: list[str] = field(default_factory=list)


def _to_int(tok: str) -> int:
    tok = tok.lower()
    return int(tok) if tok.isdigit() else WORD_NUM[tok]


def _add(d: date, n: int, unit: str) -> date:
    unit = unit.lower().rstrip("s")
    if unit == "day":
        return d + timedelta(days=n)
    if unit == "week":
        return d + timedelta(weeks=n)
    if unit == "fortnight":
        return d + timedelta(days=14 * n)
    if unit == "month":
        return d + relativedelta(months=n)
    if unit == "year":
        return d + relativedelta(years=n)
    raise ValueError(unit)


DURATION = re.compile(
    rf"within\s+(?:a\s+)?(?:further\s+)?(?:outer\s+)?(?:maximum\s+)?(?:(?:period|time)\s+of\s+)?"
    rf"(?:{NUM}\s+{UNIT}|(a|one)\s+(fortnight)|(fortnight))",
    re.I,
)
RECEIPT_COPY = re.compile(r"receipt\s+of\s+(?:a\s+)?(?:certified\s+)?(?:copy|copies)|certified\s+copy|copy\s+of\s+(?:this|the)\s+(?:order|judgment)", re.I)
RECEIPT_REPR = re.compile(r"(?:from|of)\s+(?:its|the\s+date\s+of\s+its|the)?\s*receipt|receipt\s+of\s+(?:the\s+)?(?:said\s+)?(?:legal\s+notice|representation|notice|application|claim)", re.I)
FROM_TODAY = re.compile(r"from\s+(?:today|the\s+date\s+of\s+(?:this|the)\s+(?:order|judgment)|this\s+order|the\s+date\s+of\s+passing)", re.I)
OPEN_ENDED = re.compile(r"\b(forthwith|expeditiously|at\s+the\s+earliest|as\s+early\s+as\s+possible|without\s+(?:any\s+)?(?:further\s+)?delay|in\s+a\s+time[- ]bound\s+manner)\b", re.I)


def _durations(text: str):
    out = []
    for m in DURATION.finditer(text):
        if m.group(1):
            n, unit = _to_int(m.group(1)), m.group(2)
        else:
            n, unit = 1, "fortnight"
        out.append((m, n, unit))
    return out


def compute_with_context(sentence: str, following: str, order_date: date) -> Deadline | None:
    """Directions often state the period in the next sentence ("Let the needful be done within six months...")."""
    d = compute(sentence, order_date)
    if (d is None or d.due is None) and following:
        nxt = compute(following[:300], order_date)
        if nxt and nxt.due and re.search(r"needful|the\s+same|aforesaid|above|exercise|compliance|be\s+done", following[:300], re.I):
            nxt.basis = "Period stated in the following sentence: " + nxt.basis
            return nxt
    return d


def compute(sentence: str, order_date: date) -> Deadline | None:
    """Return the deadline expressed in one direction sentence, or None if none is stated."""
    durs = _durations(sentence)
    if not durs:
        m = OPEN_ENDED.search(sentence)
        if m:
            return Deadline(m.group(0), None, "none", "open_ended",
                            f'Court said "{m.group(0)}" but gave no fixed period; tracked with a 30-day internal target.',
                            ["No fixed period in the order"])
        return None

    # Chained condition: "if a representation is filed within 4 weeks, the same be decided within 3 months from its receipt"
    if len(durs) >= 2 and RECEIPT_REPR.search(sentence[durs[0][0].end():]):
        (m1, n1, u1), (m2, n2, u2) = durs[0], durs[1]
        filed_by = _add(order_date, n1, u1)
        due = _add(filed_by, n2, u2)
        phrase = sentence[m1.start():m2.end()]
        return Deadline(
            phrase, due, "receipt_of_representation", "conditional",
            f"Petitioner may file by {filed_by:%d %b %Y} ({n1} {u1} from the order); decision due {n2} {u2} from receipt, "
            f"so latest possible due date is {due:%d %b %Y}. Exact date fixes itself when the representation is received.",
            ["Representation assumed received on the last permissible day"],
        )

    m, n, unit = durs[-1]  # the operative period is usually the last one stated
    tail = sentence[m.end(): m.end() + 120]
    if RECEIPT_COPY.search(tail):
        anchor = order_date + timedelta(days=CERTIFIED_COPY_DAYS)
        due = _add(anchor, n, unit)
        return Deadline(m.group(0), due, "receipt_of_copy", "assumed_anchor",
                        f"{n} {unit} from receipt of a copy of the order; receipt assumed {CERTIFIED_COPY_DAYS} days after "
                        f"the order ({anchor:%d %b %Y}), so due {due:%d %b %Y}. Reviewer can set the actual receipt date.",
                        [f"Copy assumed received {CERTIFIED_COPY_DAYS} days after the order"])
    if RECEIPT_REPR.search(tail):
        due = _add(order_date + timedelta(days=REPRESENTATION_DAYS), n, unit)
        return Deadline(m.group(0), due, "receipt_of_representation", "conditional",
                        f"{n} {unit} from receipt of the petitioner's representation/claim; if already received, due "
                        f"{due:%d %b %Y}. Date updates when the receipt date is entered.",
                        ["Representation assumed already received on the order date"])
    due = _add(order_date, n, unit)
    explicit = bool(FROM_TODAY.search(tail))
    return Deadline(m.group(0), due, "order_date", "exact" if explicit else "assumed_anchor",
                    f"{n} {unit} from the order dated {order_date:%d %b %Y}, so due {due:%d %b %Y}.",
                    [] if explicit else ["Period counted from the order date (no other start point stated)"])
