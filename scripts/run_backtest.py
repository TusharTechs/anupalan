"""Run Anupalan on original orders that later led to contempt petitions (P&H High Court, open data)."""
import json, os, sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from anupalan import llm
from anupalan.pipeline import process_pdf

R = "data/raw/phhc/"
pairs = pd.read_pickle(R + "backtest_pairs.pkl")
pairs["ofile"] = pairs.pdf_link.str.split("/").str[-1]
pairs = pairs[pairs.ofile.map(lambda f: os.path.exists(R + "orig/" + f))]


def run(row):
    try:
        out = process_pdf(R + "orig/" + row.ofile, row.orig_title, row.order_date)
    except Exception as e:  # keep going; report failures
        return {"file": row.file, "error": str(e)}
    filed = pd.to_datetime(row.date_of_registration, dayfirst=True).date()
    obs = out["obligations"]
    dues = sorted(o["due"] for o in obs if o["due"])
    first_due = date.fromisoformat(dues[0]) if dues else None
    return {
        "cocp_file": row.file, "cocp_title": row.title, "cocp_filed": filed.isoformat(),
        "orig_title": row.orig_title, "orig_order_date": row.order_date.isoformat(), "orig_file": row.ofile,
        "text_method": out.get("text_method"), "n_obligations": len(obs), "first_due": first_due.isoformat() if first_due else None,
        "days_order_to_contempt": (filed - row.order_date).days,
        "lead_days": (filed - first_due).days if first_due else None,
        "obligations": [{k: o[k] for k in ("text", "obligor", "action_summary", "due", "department", "government", "confidence", "source")} for o in obs],
    }


with ThreadPoolExecutor(8) as ex:
    results = list(ex.map(run, [r for _, r in pairs.iterrows()]))
os.makedirs("data/backtest", exist_ok=True)
json.dump(results, open("data/backtest/results.json", "w"), indent=1, default=str)
print("LLM usage:", llm.USAGE)
