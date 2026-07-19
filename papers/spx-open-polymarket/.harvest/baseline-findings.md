# Baseline comparison table (crowd / k=1 / logistic / SOQrates)

Produced by `backtest/baselines.py` (committed). Every number below is the
verbatim output of one run of that script on the cached dataset; nothing is
hand-adjusted.

## Test window (identical to the paper's validated reference)

- Dataset: `.cache/dataset.json` (465 days, 2024-07-26..2026-07-14, built by
  `backtest/dataset.py`).
- Paper window: the 200 trading days ending **2026-07-13** =
  **2025-09-09..2026-07-13** (matches the figure captions
  `spx_open_predictor_0000_200d` / `_0400_200d`: "200 trading days,
  2025-09-09 to 2026-07-13").
- Chronological halves: train **2025-09-09..2026-02-11** (n=100), test
  **2026-02-12..2026-07-13** (n=100). Nothing below is fitted on the test half.
- Window identity verified by exact reproduction of the paper's
  Table `tab:calibration` baseline row on this split: baseline 00:00 Brier
  **0.1785**, committed acc 80.9%, overconfident misses 6/6/3 at hours
  0/4/9, coin-flip 32%/10% — all equal to the published cells. v1.3 00:00
  Brier 0.1660 also matches exactly. Two cells drift by <=0.0005 from the
  published table (v1.2 00:00: 0.1746 here vs 0.1741 published; v1.3 04:00:
  0.1578 vs 0.1581), consistent with minor model-code drift since the paper
  run; the baseline row and the window itself reproduce exactly.

## Commands run (exact) and outputs

```
$ cd /Users/macbookpro/projects/trading/polymarket/stock
$ python3 -m backtest.baselines
paper window: 2025-09-09..2026-07-13 (200 days), test half 2026-02-12..2026-07-13 (n=100)

time (ET) method       n     acc    Brier
00:00     crowd       96   77.1%   0.1785
          k1         100   76.0%   0.2400
          logistic   100   74.0%   0.1792
          soqrates   100   77.0%   0.1660
04:00     crowd       99   79.8%   0.1559
          k1         100   79.0%   0.2100
          logistic   100   74.0%   0.1703
          soqrates   100   79.0%   0.1578
09:00     crowd       99   90.9%   0.0663
          k1         100   92.0%   0.0800
          logistic   100   91.0%   0.0680
          soqrates   100   92.0%   0.0696
09:29     crowd       99   92.9%   0.0599   (model/gap rows need minute futures: none cached)

SOQrates on the crowd-covered subset (paired cells):
  00:00  n=96  model 76.0% / 0.1715   crowd 77.1% / 0.1785
  04:00  n=99  model 78.8% / 0.1589   crowd 79.8% / 0.1559
  09:00  n=99  model 91.9% / 0.0703   crowd 90.9% / 0.0663

logistic fits (train half only): h0: b0=+0.4853 b1=+2.6818, h4: b0=+0.4405 b1=+3.1300, h9: b0=+0.2590 b1=+6.2163
```

The window-identity check (baseline/v1.2/v1.3 vs the published calibration
table) was run with the same `backtest.run.metrics` code:

```
$ python3 - <<'EOF'   # window check: last 200 dataset days ending 2026-07-13
...rows[-201:-1], split 100/100, Baseline/ModelV12/ModelV13.fit(train)...
baseline h=0 brier=0.1785 comm=80.9% oc80=6 coinflip=32%   # = published
baseline h=4 oc80=6 ; baseline h=9 oc80=3 coinflip=10%     # = published
v1.3    h=0 brier=0.1660                                    # = published
v1.2    h=0 brier=0.1746 (published 0.1741); v1.3 h=4 0.1578 (published 0.1581)
EOF
```

## Booktabs-ready table

```latex
\begin{table}[h]
    \centering
    \small
    \caption{Baselines against SOQrates on the test half
    (2026-02-12 to 2026-07-13, $n=100$ days; crowd cells on the
    crowd-covered subset, $n$ as shown). Accuracy calls UP when
    $P(\text{up})>0.5$; Brier is mean squared probability error. The
    $k{=}1$ carryover is a hard 0/1 classifier, so its Brier equals its
    miss rate.}
    \label{tab:baselines}
    \begin{tabular}{llrrr}
        \toprule
        Time (ET) & Method & $n$ & Accuracy & Brier \\
        \midrule
        00:00 & Polymarket crowd            & 96  & 77.1\% & 0.1785 \\
              & Full-gap carryover ($k{=}1$) & 100 & 76.0\% & 0.2400 \\
              & Logistic on gap             & 100 & 74.0\% & 0.1792 \\
              & SOQrates                    & 100 & 77.0\% & 0.1660 \\
        \midrule
        04:00 & Polymarket crowd            & 99  & 79.8\% & 0.1559 \\
              & Full-gap carryover ($k{=}1$) & 100 & 79.0\% & 0.2100 \\
              & Logistic on gap             & 100 & 74.0\% & 0.1703 \\
              & SOQrates                    & 100 & 79.0\% & 0.1578 \\
        \midrule
        09:00 & Polymarket crowd            & 99  & 90.9\% & 0.0663 \\
              & Full-gap carryover ($k{=}1$) & 100 & 92.0\% & 0.0800 \\
              & Logistic on gap             & 100 & 91.0\% & 0.0680 \\
              & SOQrates                    & 100 & 92.0\% & 0.0696 \\
        \midrule
        09:29 & Polymarket crowd            & 99  & 92.9\% & 0.0599 \\
              & (model / gap baselines)     & \multicolumn{3}{l}{--- no minute-level futures cached} \\
        \bottomrule
    \end{tabular}
\end{table}
```

## Per-cell provenance

**Ground truth (all cells).** Outcome = `off > 0`, where `off` is the
official ^GSPC open gap in % of prior close from `.cache/dataset.json`
(Yahoo, stooq-cross-checked). On every crowd-covered day the Polymarket
resolution (`meta.outcome_up` in `.cache/pm_history/<date>.json`) agrees
with `off > 0` (0 mismatches over the 99 covered test days).

**Scoring convention (all cells).** Same as `backtest/run.py:metrics`:
call UP iff p > 0.5; Brier = mean of (p - 1{up})^2. No day in any cell had
p exactly 0.5, so the tie convention never fires.

**Crowd rows.** P(up) = last cached CLOB book midpoint of the UP token at
or before the decision minute (ET), market date only, from
`.cache/pm_history/` (fetched previously by `pm/history.py`; no new
fetching). Coverage: 99 of 100 test days have a cached curve
(**2026-05-05 missing** — no non-empty cached history). At 00:00 three
more days have no quote by minute 0 (**2026-04-07, 2026-04-08,
2026-04-20**), hence n=96; at 04:00/09:00/09:29 all 99 covered days
quote, hence n=99. These are book midpoints, not trades (dense even on
zero-volume days).

**k=1 rows.** p = 1.0 if ES gap at the decision hour > 0 else 0.0, gap
from `dataset.json` `es[h]` (h = 0, 4, 9). Hard classifier, so Brier =
1 - accuracy by construction. Two test days have an exactly-zero 00:00
gap (2026-05-27, 2026-06-03) and are called DOWN by the p>0.5 convention.
n=100 at every hour (all test days carry hours 0/4/9).

**Logistic rows.** P(up) = sigmoid(b0 + b1 g), g = ES gap at the decision
hour; one fit per hour by Newton-Raphson (ridge 1e-6, stdlib only,
`backtest/baselines.py:fit_logistic`) on the **train half only** (n=100,
64 up). Fitted coefficients: h0 (+0.4853, +2.6818), h4 (+0.4405,
+3.1300), h9 (+0.2590, +6.2163). Evaluated on all 100 test days.

**SOQrates rows.** `model.core.ModelProd` (the paper's production
hand-off: v1.3 before 5:00 ET, v1.2 after — so 00:00/04:00 cells are
v1.3, 09:00 is v1.2), fitted on the train half only. Its 00:00 Brier
0.1660 equals the published v1.3 cell of `tab:calibration`; 04:00 is
0.1578 vs the published 0.1581 (see drift note above); the 09:00 v1.2
Brier here is 0.0696 (published table reports Brier only for v1.3 at
09:00, 0.0708).

**09:29 row.** Crowd only. BLOCKED for the model and gap baselines:
`dataset.json` carries hourly gap paths (hours 0..9) and no minute-level
futures series is cached (Yahoo keeps only ~30 days of ES minute bars,
none stored). The paper's ~94% at 9:29 comes from a separate n=18
minute-level live sample and is not recomputable on this window.

**Paired subset (footnote material).** Restricting SOQrates to the exact
crowd-covered days: 00:00 (n=96) model 76.0%/0.1715 vs crowd
77.1%/0.1785; 04:00 (n=99) model 78.8%/0.1589 vs crowd 79.8%/0.1559;
09:00 (n=99) model 91.9%/0.0703 vs crowd 90.9%/0.0663. Honest headline:
on matched days the crowd is slightly more accurate pre-open and
better-calibrated from 04:00 on; SOQrates wins midnight calibration and
09:00 accuracy. The model's edge in the paper is the trading rule
(confidence gate + edge threshold vs the quoted price), not raw
crowd-beating accuracy at every hour.

## BLOCKED cells

- 09:29 x {k=1, logistic, SOQrates}: no minute-level futures data in the
  cached dataset (hourly gap paths only; ~30-day Yahoo ES minute cap, not
  cached), so no gap or model prediction exists at 9:29 for this window.
- Nothing else is blocked: crowd curves cover 99/100 test days from the
  existing `.cache/pm_history/` cache; no network fetches were made.
