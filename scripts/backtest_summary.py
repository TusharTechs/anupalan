"""Summarise data/backtest/results.json for the app, the dossier and the video."""
import json
import pandas as pd

r = [x for x in json.load(open("data/backtest/results.json")) if "error" not in x]
d = pd.DataFrame(r)
cap = d.n_obligations > 0
dated = d.first_due.notna()
before = dated & (d.lead_days > 0)
bins = [(-10**6, 0, "before deadline"), (1, 30, "1-30"), (31, 60, "31-60"), (61, 90, "61-90"), (91, 180, "91-180"), (181, 365, "181-365"), (366, 10**6, ">1 year")]
hist = [{"label": l, "count": int(((d.lead_days >= a) & (d.lead_days <= b)).sum())} for a, b, l in bins]
ex = d[before & d.obligations.map(lambda o: bool(o and o[0].get("action_summary")))].sample(14, random_state=8).sort_values("lead_days", ascending=False)
summary = {
    "cases": int(len(d)),
    "captured": int(cap.sum()), "captured_pct": round(cap.mean() * 100),
    "direct_pct": round(d.obligations.map(lambda ob: any("reference" not in (o["source"] or "") for o in ob)).mean() * 100),
    "dated": int(dated.sum()), "dated_pct": round(dated.mean() * 100),
    "deadline_before_contempt": int(before.sum()), "deadline_before_contempt_pct": round(before.sum() / dated.sum() * 100),
    "median_lead_days": int(d[before].lead_days.median()),
    "median_order_to_contempt_days": int(d.days_order_to_contempt.median()),
    "histogram": hist,
    "method": ("Contempt petitions (COCP) with an order in 2025 were sampled from the open Punjab & Haryana High Court dataset (CC-BY-4.0). "
               "Where the contempt order names the original order allegedly disobeyed, that original order (2022-2025) was located in the same "
               f"dataset and processed by Anupalan exactly as a new order would be. {len(d)} original orders were analysed."),
    "examples": [{"orig_title": e.orig_title, "orig_order_date": e.orig_order_date, "first_due": e.first_due, "cocp_filed": e.cocp_filed,
                  "lead_days": int(e.lead_days), "summary": e.obligations[0]["action_summary"], "obligor": e.obligations[0]["obligor"]}
                 for e in ex.itertuples()],
}
json.dump(summary, open("data/backtest/summary.json", "w"), indent=1)
print({k: v for k, v in summary.items() if k not in ("histogram", "examples", "method")})
print(summary["histogram"])
