"""SQLite obligation register with a full audit trail."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "data" / "anupalan.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
  id INTEGER PRIMARY KEY, case_no TEXT, title TEXT, decision_date TEXT, petitioner TEXT, respondents TEXT,
  governments TEXT, judge TEXT, text TEXT, text_method TEXT, source TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS obligations (
  id INTEGER PRIMARY KEY, order_id INTEGER REFERENCES orders(id), text TEXT, start INTEGER, "end" INTEGER,
  obligor TEXT, action_type TEXT, action_summary TEXT, beneficiary TEXT, conditions TEXT,
  due TEXT, deadline TEXT, government TEXT, department TEXT, department_evidence TEXT,
  confidence REAL, review_required INTEGER, alerts TEXT, source TEXT, ref_case TEXT,
  review_status TEXT DEFAULT 'pending',      -- pending | confirmed | edited | rejected
  compliance_status TEXT DEFAULT 'open',     -- open | in_progress | complied | under_appeal | stayed
  updated_at TEXT
);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY, obligation_id INTEGER, ts TEXT, actor TEXT, action TEXT, detail TEXT
);
"""


def conn(path: Path = DB) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(path, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    return c


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def save_order(c: sqlite3.Connection, order: dict, source: str = "") -> int:
    cur = c.execute(
        "INSERT INTO orders (case_no,title,decision_date,petitioner,respondents,governments,judge,text,text_method,source,created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (order.get("case_no"), order.get("title"), order.get("decision_date"), order.get("petitioner"), order.get("respondents"),
         json.dumps(order.get("governments", [])), order.get("judge"), order.get("text"), order.get("text_method"), source, now()),
    )
    oid = cur.lastrowid
    for o in order.get("obligations", []):
        cur = c.execute(
            'INSERT INTO obligations (order_id,text,start,"end",obligor,action_type,action_summary,beneficiary,conditions,due,deadline,'
            "government,department,department_evidence,confidence,review_required,alerts,source,ref_case,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (oid, o["text"], o["start"], o["end"], o.get("obligor"), o.get("action_type"), o.get("action_summary"), o.get("beneficiary"),
             o.get("conditions"), o.get("due"), json.dumps(o.get("deadline"), default=str), o.get("government"), o.get("department"),
             o.get("department_evidence"), o.get("confidence"), int(bool(o.get("review_required"))), json.dumps(o.get("alerts")),
             o.get("source"), o.get("ref_case"), now()),
        )
        log(c, cur.lastrowid, "anupalan", "extracted", f"{o.get('source')} confidence {o.get('confidence')}")
    c.commit()
    return oid


def log(c, obligation_id: int, actor: str, action: str, detail: str = ""):
    c.execute("INSERT INTO events (obligation_id,ts,actor,action,detail) VALUES (?,?,?,?,?)", (obligation_id, now(), actor, action, detail))


def row(r: sqlite3.Row) -> dict:
    d = dict(r)
    for k in ("deadline", "alerts", "governments"):
        if k in d and isinstance(d[k], str):
            try:
                d[k] = json.loads(d[k])
            except json.JSONDecodeError:
                pass
    return d
