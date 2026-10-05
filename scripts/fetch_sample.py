"""Download P&H High Court metadata (2022-2025) and the sampled order PDFs from the open dataset (no AWS account needed)."""
import os, subprocess
import pandas as pd

R = "data/raw/phhc/"
B = "s3://indian-high-court-judgments"
os.makedirs(R + "pdf", exist_ok=True)


def cp(src, dst):
    if not os.path.exists(dst):
        subprocess.run(["aws", "s3", "cp", "--no-sign-request", "--quiet", src, dst], check=False)


cp(f"{B}/metadata/parquet/year=2025/court=3_22/bench=phhc/metadata.parquet", R + "phhc_2025.parquet")
for y in (2022, 2023, 2024):
    cp(f"{B}/metadata/parquet/year={y}/court=3_22/bench=phhc/metadata.parquet", R + f"phhc_{y}_bench=phhc.parquet")
if not os.path.exists(R + "sample_index.csv"):
    d = pd.read_parquet(R + "phhc_2025.parquet")
    d["file"] = d.pdf_link.str.split("/").str[-1]
    gov = r"STATE OF PUNJAB|STATE OF HARYANA|U\.?T\.? CHANDIGARH|UNION OF INDIA|PUNJAB STATE|HARYANA STATE"
    cwp = d[d.title.str.match(r"^CWP/", na=False) & d.title.str.contains(gov, case=False, na=False) & d.disposal_nature.isin(["DISPOSED OF", "ALLOWED"])]
    cocp = d[d.title.str.match(r"^COCP/", na=False)]
    s = pd.concat([cwp.sample(400, random_state=7).assign(kind="CWP"), cocp.sample(300, random_state=7).assign(kind="COCP")])
    s[["kind", "title", "cnr", "date_of_registration", "decision_date", "disposal_nature", "judge", "file", "pdf_link"]].to_csv(R + "sample_index.csv", index=False)
for f in pd.read_csv(R + "sample_index.csv").file:
    cp(f"{B}/data/pdf/year=2025/court=3_22/bench=phhc/{f}", R + "pdf/" + f)
print("done")
