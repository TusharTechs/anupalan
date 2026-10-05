"""Process the sampled P&H High Court writ orders (open data, 2025) into the register."""
import os, sys
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from anupalan import llm, store
from anupalan.pipeline import process_pdf

R = "data/raw/phhc/"
s = pd.read_csv(R + "sample_index.csv")
s = s[s.kind == "CWP"]
if os.path.exists(store.DB):
    os.remove(store.DB)
c = store.conn()


import json
CACHE = "data/cache/"
os.makedirs(CACHE, exist_ok=True)


def run(r):
    f = CACHE + r.file + ".json"
    if os.path.exists(f):
        return r, json.load(open(f))
    try:
        out = process_pdf(R + "pdf/" + r.file, r.title, pd.to_datetime(r.decision_date).date())
    except Exception:
        return r, None
    out = json.loads(json.dumps(out, default=str))
    json.dump(out, open(f, "w"))
    return r, out


with ThreadPoolExecutor(8) as ex:
    for r, out in ex.map(run, [r for _, r in s.iterrows()]):
        if out:
            for o in out["obligations"]:  # apply current mapping policy to cached results
                if o.get("llm_department") and o["llm_department"] != "Other":
                    o["department"], o["department_evidence"] = o["llm_department"], "AI reading of the direction and parties (confirm)"
            out["case_no"] = out["case_no"] or r.title.split(" of ")[0]
            store.save_order(c, out, source=f"open-data:phhc:{r.file}")
print("orders", c.execute("select count(*) from orders").fetchone()[0], "obligations", c.execute("select count(*) from obligations").fetchone()[0])
print("LLM usage:", llm.USAGE)
