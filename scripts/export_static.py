"""Export a read-only snapshot of the register for the public static demo (GitHub Pages)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("ANUPALAN_AS_OF", "2025-10-01")
from anupalan import app as A

out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "demo")
os.makedirs(out + "/orders", exist_ok=True)
w = lambda p, d: json.dump(d, open(os.path.join(out, p), "w"), default=str)
w("dashboard.json", A.dashboard())
w("obligations.json", A.obligations())
w("backtest.json", A.backtest())
for (oid,) in A.db.execute("SELECT id FROM orders WHERE id IN (SELECT DISTINCT order_id FROM obligations)"):
    w(f"orders/{oid}.json", A.order(oid))
print("exported", len(os.listdir(out + "/orders")), "orders")
