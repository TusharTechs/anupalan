"""FastAPI service: upload orders, review extracted obligations, track compliance."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import date, timedelta
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import store
from .pipeline import process_pdf

ROOT = Path(__file__).resolve().parent.parent
AS_OF = date.fromisoformat(os.environ.get("ANUPALAN_AS_OF", date.today().isoformat()))

app = FastAPI(title="Anupalan", version="0.1.0")
db = store.conn()


def _status(o: dict) -> str:
    if o["review_status"] == "rejected":
        return "rejected"
    if o["compliance_status"] in ("complied", "stayed", "under_appeal"):
        return o["compliance_status"]
    if not o["due"]:
        return "no_fixed_deadline"
    d = date.fromisoformat(o["due"])
    if d < AS_OF:
        return "overdue"
    if d <= AS_OF + timedelta(days=30):
        return "due_30d"
    return "open"


def _obligations(where: str = "", args: tuple = ()) -> list[dict]:
    q = ("SELECT ob.*, o.case_no, o.title, o.decision_date, o.petitioner FROM obligations ob JOIN orders o ON o.id = ob.order_id "
         + where + " ORDER BY ob.due IS NULL, ob.due")
    out = []
    for r in db.execute(q, args):
        d = store.row(r)
        d["status"] = _status(d)
        out.append(d)
    return out


@app.get("/api/meta")
def meta():
    return {"as_of": AS_OF.isoformat(), "orders": db.execute("SELECT COUNT(*) FROM orders").fetchone()[0]}


@app.get("/api/dashboard")
def dashboard():
    obs = [o for o in _obligations() if o["review_status"] != "rejected"]
    by_dept: dict[str, dict] = {}
    for o in obs:
        k = f'{o["government"]} | {o["department"]}'
        dd = by_dept.setdefault(k, {"government": o["government"], "department": o["department"], "total": 0, "overdue": 0, "due_30d": 0, "complied": 0})
        dd["total"] += 1
        if o["status"] in ("overdue", "due_30d", "complied"):
            dd[o["status"]] += 1
    counts = {s: sum(1 for o in obs if o["status"] == s) for s in ("overdue", "due_30d", "open", "no_fixed_deadline", "complied")}
    return {
        "as_of": AS_OF.isoformat(),
        "orders": db.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
        "obligations": len(obs),
        "pending_review": sum(1 for o in obs if o["review_status"] == "pending"),
        "counts": counts,
        "departments": sorted(by_dept.values(), key=lambda x: (-x["overdue"], -x["total"])),
        "upcoming": ([o for o in obs if o["status"] == "due_30d"]
                     + sorted([o for o in obs if o["status"] == "overdue"], key=lambda o: o["due"], reverse=True))[:12],
    }


@app.get("/api/obligations")
def obligations(status: str | None = None, review: str | None = None, department: str | None = None, q: str | None = None):
    obs = _obligations()
    if status:
        obs = [o for o in obs if o["status"] == status]
    if review:
        obs = [o for o in obs if o["review_status"] == review]
    if department:
        obs = [o for o in obs if o["department"] == department]
    if q:
        ql = q.lower()
        obs = [o for o in obs if ql in (o["title"] or "").lower() or ql in (o["text"] or "").lower() or ql in (o["obligor"] or "").lower()]
    return obs


@app.get("/api/orders/{order_id}")
def order(order_id: int):
    r = db.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    if not r:
        raise HTTPException(404)
    o = store.row(r)
    o["obligations"] = _obligations("WHERE ob.order_id=?", (order_id,))
    return o


@app.get("/api/obligations/{oid}/events")
def events(oid: int):
    return [dict(r) for r in db.execute("SELECT * FROM events WHERE obligation_id=? ORDER BY id", (oid,))]


class Review(BaseModel):
    action: str                     # confirm | reject | edit | status
    reviewer: str = "legal-officer"
    due: str | None = None
    department: str | None = None
    obligor: str | None = None
    action_summary: str | None = None
    compliance_status: str | None = None
    note: str = ""


@app.post("/api/obligations/{oid}/review")
def review(oid: int, r: Review):
    if not db.execute("SELECT 1 FROM obligations WHERE id=?", (oid,)).fetchone():
        raise HTTPException(404)
    sets, args, changes = [], [], []
    for f in ("due", "department", "obligor", "action_summary", "compliance_status"):
        v = getattr(r, f)
        if v is not None:
            sets.append(f"{f}=?"); args.append(v); changes.append(f"{f}={v}")
    if r.action in ("confirm", "edit"):
        sets.append("review_status=?"); args.append("edited" if changes and r.action == "edit" else "confirmed")
    elif r.action == "reject":
        sets.append("review_status=?"); args.append("rejected")
    sets.append("updated_at=?"); args.append(store.now())
    db.execute(f"UPDATE obligations SET {', '.join(sets)} WHERE id=?", (*args, oid))
    store.log(db, oid, r.reviewer, r.action, "; ".join(changes + ([r.note] if r.note else [])))
    db.commit()
    return _obligations("WHERE ob.id=?", (oid,))[0]


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "PDF only")
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
    try:
        out = process_pdf(tmp.name, title=file.filename)
    finally:
        os.unlink(tmp.name)
    oid = store.save_order(db, out, source=f"upload:{file.filename}")
    return order(oid)


@app.get("/api/metrics")
def metrics():
    """Precision from human review decisions (confirmed, edited or rejected)."""
    rows = [dict(r) for r in db.execute("SELECT review_status, due, deadline FROM obligations WHERE review_status != 'pending'")]
    n = len(rows)
    ok = sum(1 for r in rows if r["review_status"] == "confirmed")
    edited = sum(1 for r in rows if r["review_status"] == "edited")
    rejected = sum(1 for r in rows if r["review_status"] == "rejected")
    return {"reviewed": n, "confirmed_unchanged": ok, "edited": edited, "rejected": rejected,
            "precision_task_is_real": round((ok + edited) / n, 3) if n else None,
            "exact_without_edits": round(ok / n, 3) if n else None}


@app.get("/api/backtest")
def backtest():
    f = ROOT / "data" / "backtest" / "summary.json"
    return json.loads(f.read_text()) if f.exists() else {}


app.mount("/", StaticFiles(directory=ROOT / "web", html=True), name="web")
