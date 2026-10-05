"""Optional LLM structuring layer.

The LLM receives the order and the rule engine's candidate sentences and returns
structured obligations as JSON. Guard rails:
  * every `direction_quote` must appear verbatim in the order, or the item is dropped;
  * the LLM never computes dates (deadline.py does);
  * low confidence always routes to human review.
Backends: Anthropic API (ANTHROPIC_API_KEY in env or ~/.anupalan.env) or the
`claude` CLI for local development. With neither, the pipeline runs rules-only.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

MODEL = os.environ.get("ANUPALAN_MODEL", "claude-haiku-4-5-20251001")
USAGE = {"calls": 0, "input_tokens": 0, "output_tokens": 0}

SYSTEM = """You extract court-ordered obligations from Indian High Court orders for a government compliance register.
An obligation is something the COURT directs a government authority/respondent to do (decide, pay, release, grant, reconsider, report...).
Ignore: counsel's submissions or prayers, liberty given to the petitioner, dismissals, notices issued for the next hearing, directions to the Registry.
Return ONLY JSON: {"obligations":[{"direction_quote": "<exact sentence(s) copied verbatim from the order>",
"obligor": "<authority directed, as named in the order, e.g. 'Respondent No.2 - Director, School Education, Punjab' or 'State of Punjab and PSPCL'>",
"action_summary": "<what must be done, max 20 words, plain English>",
"beneficiary": "<who benefits>", "conditions": "<conditions or 'none'>",
"deadline_phrase": "<the exact time phrase from the quote, or 'none'>",
"department": "<one of: School Education, Higher Education, Health & Family Welfare, Police / Home, Finance / Pensions, Revenue & Disaster Mgmt, Power (PSPCL / Nigams), Rural Development & Panchayats, Local Government / Urban, Irrigation / Water Resources, Transport, Agriculture & Cooperation, Forests & Environment, Social Justice & Welfare, Defence (Union), Recruitment Commissions (HPSC/HSSC/PPSC/PSSSB), Personnel / General Admin, Other>",
"confidence": <0..1>}]}
If there is no obligation, return {"obligations": []}. Copy quotes exactly; do not paraphrase inside direction_quote."""


def _load_key() -> str | None:
    for var in ("ANTHROPIC_API_KEY", "LLM_API_KEY"):
        if os.environ.get(var):
            return os.environ[var]
    for f in (Path(__file__).resolve().parent.parent / ".env", Path.home() / ".anupalan.env"):
        if f.exists():
            for line in f.read_text().splitlines():
                line = line.strip().removeprefix("export ").strip()
                if line.startswith(("ANTHROPIC_API_KEY=", "LLM_API_KEY=")):
                    return line.split("=", 1)[1].strip().strip("'\"")
    return None


def backend() -> str:
    if os.environ.get("ANUPALAN_LLM") == "none":
        return "none"
    if _load_key():
        return "anthropic"
    if os.environ.get("ANUPALAN_LLM") == "claude-cli" and shutil.which("claude"):
        return "claude-cli"
    return "none"


def _prompt(order_text: str, candidates: list[str]) -> str:
    cand = "\n".join(f"- {c}" for c in candidates) or "- (none found by rules)"
    return f"ORDER TEXT:\n<<<\n{order_text[:14000]}\n>>>\n\nRULE-ENGINE CANDIDATE SENTENCES:\n{cand}\n\nReturn the JSON now."


def _parse(raw: str) -> list[dict]:
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        return []
    try:
        return json.loads(m.group(0)).get("obligations", [])
    except json.JSONDecodeError:
        return []


def _norm(s: str) -> str:
    return re.sub(r"\W+", " ", s).lower().strip()


def _grounded(q: str, hay: str) -> bool:
    """Quote must appear verbatim, allowing only for paragraph numbers/line noise the LLM skipped:
    its first and last 6 words must occur in order, within a window close to the quote's length."""
    if len(q) < 20:
        return False
    if q in hay:
        return True
    w = q.split()
    if len(w) < 12:
        return False
    head, tail = " ".join(w[:6]), " ".join(w[-6:])
    i = hay.find(head)
    while i >= 0:
        j = hay.find(tail, i)
        if j >= 0 and (j + len(tail) - i) <= len(q) * 1.25 + 40:
            return True
        i = hay.find(head, i + 1)
    return False


def verify_quotes(items: list[dict], order_text: str) -> list[dict]:
    """Drop any item whose quote is not found in the order (hallucination guard)."""
    hay = _norm(order_text)
    return [it for it in items if _grounded(_norm(it.get("direction_quote", "")), hay)]


def extract(order_text: str, candidates: list[str]) -> tuple[list[dict], str]:
    b = backend()
    if b == "none":
        return [], b
    prompt = _prompt(order_text, candidates)
    if b == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=_load_key())
        msg = client.messages.create(model=MODEL, max_tokens=1500, system=SYSTEM,
                                     messages=[{"role": "user", "content": prompt}])
        raw = "".join(blk.text for blk in msg.content if getattr(blk, "type", "") == "text")
        USAGE["calls"] += 1
        USAGE["input_tokens"] += msg.usage.input_tokens
        USAGE["output_tokens"] += msg.usage.output_tokens
    else:
        r = subprocess.run(["claude", "-p", "--model", "haiku", "--append-system-prompt", SYSTEM, prompt],
                           capture_output=True, text=True, timeout=180)
        raw = r.stdout
    return verify_quotes(_parse(raw), order_text), b
