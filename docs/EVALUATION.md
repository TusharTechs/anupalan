# Evaluation: method, results, limits

All numbers come from public Punjab & Haryana High Court orders in the open
[Indian High Court Judgments](https://registry.opendata.aws/indian-high-court-judgments/) dataset (CC-BY-4.0), processed by the code in this repository in October 2026.

## 1. Contempt backtest (does it catch the directions that actually get violated?)

**Question.** If Anupalan had been running, would it have extracted the court's direction and computed a deadline early enough to warn the department before the citizen had to file contempt?

**Method.**
1. Sampled 1,800 contempt (COCP) orders dated 2025 from the dataset (random, seed fixed in the scripts).
2. `anupalan/backtest.py` reads each COCP order and finds the original order it says was disobeyed, e.g. "non-compliance of the order dated 29.04.2024 passed in CWP-9594-2024". 551 of 1,800 orders name one. Most of the rest are adjournment orders that restate nothing.
3. For originals dated 2022–2025 in CWP/LPA cases (439), the original order was looked up in the same dataset by case number and date: **293 located and analysed**.
4. Each original order was processed by the full pipeline (text/OCR → rules → Claude Haiku 4.5 → deadline engine), with no knowledge of the later contempt case.
5. Compared: extracted deadline vs the date the contempt petition was registered.

**Results (n = 293).**

| Metric | Value |
|---|---|
| Direction captured (directly, or by linking an order "disposed of in terms of CWP-X") | **265 (90%)**; direct 84% |
| Deadline computed | **192 (66%)**. The rest have no time limit in the order ("in accordance with law"); Anupalan applies a 30-day internal target |
| Deadline passed before contempt was filed | **185 of 192 (96%)** |
| Median time between computed deadline and contempt filing | **89 days** |
| Median time from original order to contempt filing | **177 days** |

Distribution of (contempt filing date − computed deadline): before deadline 7 · 1–30 days 40 · 31–60 27 · 61–90 26 · 91–180 38 · 181–365 30 · over 1 year 24.

**What this does and does not show.** It shows the system finds the obligation that later became a contempt case, and that a dated warning would have existed weeks to months earlier. It does not prove contempt would have been avoided: that depends on the department acting. "Captured" here means the pipeline produced an obligation for the order. A sample of captured obligations was spot-checked against the order text; a formal precision study is section 3.

## 2. Forward run on new orders

400 randomly sampled 2025 writ (CWP) orders with a State/Union party, disposed of or allowed: **427 obligations from 257 orders (64%)**, 243 with a computed deadline. Replaying the register as of 1 Oct 2025: 117 overdue, 38 due within 30 days, 184 with no fixed deadline.

## 3. Human review (precision): in progress

Precision is measured the honest way: a person confirms, edits or rejects extracted obligations in the review queue, and the app logs every decision. Planned: 100 randomly ordered obligations reviewed by the developer, plus a blind review of 30 by a practising lawyer or legal-cell officer. Results will be added to this file with the review log.

## 4. Cost and speed (measured)

| | Value |
|---|---|
| Tokens per order (Claude Haiku 4.5) | ~1,250–1,450 input, ~230–290 output |
| Cost per order | ≈ US$0.0024–0.0029 ≈ ₹0.23–0.28 (list price $1 / $5 per million tokens; ₹96.2 per USD); half with the Batch API |
| End-to-end time per order (upload → obligations) | ~3 seconds |
| Whole backtest (293 orders) | ≈ US$0.85 |

## 5. Known limits

* Orders with no stated time limit cannot have a court deadline; they get an internal target and are flagged.
* "From receipt of certified copy" deadlines assume receipt 7 days after the order until an officer enters the actual date.
* Department mapping is a suggestion (AI reading of the direction and parties); officers confirm it.
* Some PDFs in the dataset have broken text layers; OCR recovers most of them but quality varies.
* The dataset may not contain every order of the court, and contempt cases filed after the data cut-off are not visible.
