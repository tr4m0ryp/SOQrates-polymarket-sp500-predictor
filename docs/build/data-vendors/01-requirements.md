# 01 · What data the auction layer needs

**Goal:** reconstruct the official S&P 500 9:30 ET opening print from constituent auction
data, earlier and better than the futures-watching crowd. The core model (futures + regime
sigma + news) runs on free data already; this layer is the auction-quirk edge.

## The four data types

For **S&P 500 constituents**, in the **9:15–9:40 ET** window:

| # | Data | Exact fields | Why |
|---|---|---|---|
| **1** | **Nasdaq NOII** | near/far indicative price, reference price, paired shares, imbalance shares, imbalance side | The pre-open *predictive* signal for Nasdaq-listed names (from 9:25, 1/sec from 9:28) |
| **2** | **NYSE opening imbalance** | reference price, paired qty, indicative match/clearing price | Same signal for NYSE-listed names |
| **3** | **Per-stock opening cross print + timestamp** | realized 9:30 price + exact ts + venue | Ground-truth target; the timestamp fits the per-stock print-timing model |
| **4** | **Pre-open NBBO quote midpoints** | bid/ask/mid per constituent | Fresh quote to cut sigma before 9:28 (Track-1 assist) |

Each type is needed in **two modes**:
- **Historical** — validate the replica + fit the timing/noise models on ~12–60 days incl. quirk days.
- **Live** — one prediction/day, streaming only 9:25–9:31.

## Signal weighting

**Nasdaq NOII (#1) is the highest-value leg** — Nasdaq-listed mega-caps carry ~57% of index
weight and their NOII deviates only ~2–5bp from the print (vs 30–100bp for NYSE). This is why
the Nasdaq NOII gap in any source matters most.

## Pipeline seams the data must satisfy

The auction data must slot into the existing stage-3 pipeline unchanged:

- **`stage3`** builds two dicts per date: `pred = {ticker: indicative_price}` and
  `closes = {ticker: prior_close}`, then calls `pipeline.replica_estimate` /
  `pipeline.replica_distribution`.
- Today `pred` comes from `lseg_parse.snapshots(path) -> {ticker: [{'pred_open': float, ...}]}`
  (stage3 takes the last snapshot with `pred_open`). **Any new source must emit this shape.**
- `pred_open` = the **indicative clearing price** (NOII near/indicative), not the realized print.
- `timing.fit_from_prints()` / `montecarlo.apply_prints()` want realized crosses as
  `{ticker: (price, ts_ns)}` — this is #3-with-timestamp.
- Nasdaq trusted at indicative; NYSE default-stale unless proven (`pipeline.NYSE_TRUST_DEFAULT`).

## Scope constraints

- All timestamps ET (`America/New_York`). Gaps in % of prior close.
- One prediction/day; per-second data only in the 9:28–9:30 window.
- Filtered pulls only (~500 symbols × 25-min window) — never full-market ITCH (4–5 GB/day).
