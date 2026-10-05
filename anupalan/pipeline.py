"""Order -> obligations. Rules find and date; the LLM (optional) structures; humans confirm."""
from __future__ import annotations

import re
from dataclasses import asdict
from datetime import date, timedelta

from . import deadline, directions, llm, mapping, meta, textprep


def alert_schedule(issued: date, due: date | None) -> list[dict]:
    if not due:
        return [{"on": (issued + timedelta(days=1)).isoformat(), "kind": "assigned"},
                {"on": (issued + timedelta(days=30)).isoformat(), "kind": "internal target (no fixed court deadline)"}]
    span = (due - issued).days
    points = [d for d in (30, 15, 7, 2) if d < span]
    if span <= 30:
        points = sorted({max(1, span // 2), 2} - {0}, reverse=True)
    out = [{"on": (issued + timedelta(days=1)).isoformat(), "kind": "assigned"}]
    out += [{"on": (due - timedelta(days=d)).isoformat(), "kind": f"{d} days to deadline"} for d in points]
    out += [{"on": (due + timedelta(days=1)).isoformat(), "kind": "overdue: escalate to head of department"}]
    return out


def _overlaps(d, item) -> bool:
    if item["start"] >= 0 and item["start"] < d.end and d.start < item["end"]:
        return True
    a, b = set(re.findall(r"\w+", d.text.lower())), set(re.findall(r"\w+", item["text"].lower()))
    return len(a & b) / max(min(len(a), len(b)), 1) > 0.6


def _span(text: str, quote: str) -> tuple[int, int]:
    i = text.find(quote)
    if i >= 0:
        return i, i + len(quote)
    words = re.findall(r"\w+", quote)
    if len(words) >= 4:
        pat = r"\W+".join(map(re.escape, words[:8]))
        m = re.search(pat, text)
        if m:
            end_pat = r"\W+".join(map(re.escape, words[-6:]))
            e = re.search(end_pat, text[m.start():])
            return m.start(), m.start() + (e.end() if e else len(quote))
    return -1, -1


def process_text(raw_text: str, title: str | None = None, decision_date: date | None = None, use_llm: bool = True) -> dict:
    text = textprep.flow(raw_text)
    m = meta.parse(raw_text, title)
    od = decision_date or m.decision_date or date.today()
    rule_hits = directions.find(text)
    items, source = [], "rules"
    if use_llm:
        llm_items, b = llm.extract(text, [d.text for d in rule_hits])
        if b != "none":
            source = f"llm:{b}+rules"
            for it in llm_items:
                q = it["direction_quote"]
                s, e = _span(text, q)
                items.append({"text": q, "start": s, "end": e, "obligor": it.get("obligor"),
                              "action_summary": it.get("action_summary"), "beneficiary": it.get("beneficiary"),
                              "conditions": it.get("conditions"), "confidence": float(it.get("confidence", 0.7)),
                              "action_type": directions.classify(q), "llm_department": it.get("department")})
            # keep strong rule hits the LLM missed (e.g. noisy OCR); they go to human review
            for d in rule_hits:
                if d.strength >= 0.8 and not any(_overlaps(d, i) for i in items):
                    items.append({"text": d.text, "start": d.start, "end": d.end, "obligor": m.respondents,
                                  "action_summary": None, "beneficiary": m.petitioner, "conditions": None,
                                  "confidence": min(d.strength, 0.7), "action_type": d.action_type, "rule_only": True})
    if source == "rules":
        for d in rule_hits:
            items.append({"text": d.text, "start": d.start, "end": d.end, "obligor": m.respondents,
                          "action_summary": None, "beneficiary": m.petitioner, "conditions": None,
                          "confidence": d.strength, "action_type": d.action_type})
    obligations = []
    for it in items:
        dl = deadline.compute_with_context(it["text"], text[it["end"]:it["end"] + 300] if it["end"] > 0 else "", od)
        mp = mapping.suggest(it["text"], m.respondents, text, m.governments)
        if it.get("llm_department") and it["llm_department"] != "Other":
            mp = {**mp, "department": it["llm_department"], "evidence": "AI reading of the direction and parties (confirm)", "confidence": 0.75}
        conf = it["confidence"] * (1.0 if dl and dl.due else 0.85)
        obligations.append({
            **it,
            "deadline": asdict(dl) if dl else None,
            "due": dl.due.isoformat() if dl and dl.due else None,
            "government": mp["government"], "department": mp["department"], "department_evidence": mp["evidence"],
            "confidence": round(conf, 2),
            "review_required": conf < 0.85 or not (dl and dl.due) or mp["confidence"] < 0.6,
            "alerts": alert_schedule(od, dl.due if dl else None),
            "source": source,
        })
    for ref in directions.find_references(text):
        if any(o["start"] <= ref["start"] < o["end"] for o in obligations):
            continue
        rd = meta.parse_date(ref["ref_date"]) if ref["ref_date"] else None
        obligations.append({
            "text": ref["text"], "start": ref["start"], "end": ref["end"], "obligor": m.respondents,
            "action_summary": f"Comply with the directions in {ref['ref_case']}" + (f" (order dated {rd:%d.%m.%Y})" if rd else "") + "; fetched and linked for review",
            "beneficiary": m.petitioner, "conditions": None, "confidence": 0.6, "action_type": "Direction by reference",
            "ref_case": ref["ref_case"], "ref_date": rd.isoformat() if rd else None,
            "deadline": None, "due": None, "government": (m.governments or ["Unspecified government"])[0],
            "department": "To be assigned", "department_evidence": "inherits from referenced judgment",
            "review_required": True, "alerts": alert_schedule(od, None), "source": "rules:reference",
        })
    return {
        "case_no": m.case_no, "case_type": m.case_type, "title": title,
        "decision_date": od.isoformat(), "petitioner": m.petitioner, "respondents": m.respondents,
        "governments": m.governments, "judge": m.judge, "text": text, "obligations": obligations,
    }


def process_pdf(path, title=None, decision_date=None, use_llm=True) -> dict:
    raw, method = textprep.pdf_to_text(path)
    out = process_text(raw, title, decision_date, use_llm)
    out["text_method"] = method
    return out
