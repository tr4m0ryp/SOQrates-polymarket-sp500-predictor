# Statistical rigor computations — SOQrates paper

Run 2026-07-19 from the repo root `/Users/macbookpro/projects/trading/polymarket/stock`.
All numbers recomputed from the repo's own caches: `.cache/dataset.json`
(465 rows, 2024-07-26..2026-07-14) and `.cache/strategy_days.json`
(115 market days, 2026-01-22..2026-07-14; train 57 / test 58 split at
2026-04-16). No paper `.tex` file was touched.

Wilson score interval: z = 1.959964, center `(p + z²/2n)/(1 + z²/n)`,
half-width `z·sqrt(p(1−p)/n + z²/4n²)/(1 + z²/n)` — implemented in
`backtest/plot.py::wilson`.

The paper's 200-day window is recovered exactly inside the current dataset:
rows sliced by date to 2025-09-09..2026-07-13 give exactly 200 rows
(the window named in the figure captions). "Test half" below always means
the last 100 of those 200 days (2026-02-12..2026-07-13), the paper's
validated reference; models are fitted on the first 100 only.

## 1. Claim table (point, n, 95% Wilson CI, provenance)

Recomputed = derived from the current dataset caches with repo code.
Where recomputed and claimed differ, both are shown.

| Claim (abstract.tex / results.tex) | Paper point | Recomputed | n | 95% Wilson CI (recomputed) | Provenance |
|---|---|---|---|---|---|
| Midnight accuracy, 200 d | 72.5% | 145/200 = 72.5% (exact match) | 200 | [65.9%, 78.2%] | cmd A below; frozen core sign(a0+k·gap), a0=0.0092, k=0.767 |
| 04:00 accuracy, 200 d | 77.0% (154/200) | 153/200 = 76.5% (1 day off) | 200 | [70.2%, 81.8%] (claimed 154/200: [70.7%, 82.3%]) | cmd A |
| 06:00 accuracy, 200 d | 82% | 163/200 = 81.5% | 200 | [75.5%, 86.3%] | cmd A |
| 07:00 accuracy, 200 d | 85% | 168/200 = 84.0% | 200 | [78.3%, 88.4%] | cmd A |
| 09:00 accuracy, 200 d | 90% | 178/200 = 89.0% | 200 | [83.9%, 92.6%] | cmd A |
| 9:29 accuracy, minute-level | ~94% | BLOCKED — 18-day minute sample not retained in any repo cache; 17/18 = 94.4% is the unique count consistent with "~94%, n=18" | 18 | [74.2%, 99.0%] (arithmetic on inferred 17/18) | manifest.json notes: producer script/data ephemeral |
| Ceiling, perfect 9:30 data | 96.3% | BLOCKED — 81-day auction sample not in repo; 78/81 = 96.30% is the unique consistent count | 81 | [89.7%, 98.7%] (arithmetic on inferred 78/81) | approach.tex appendix; data not retained |
| Confident-days split (midnight conf ≥ 0.65) | 82.1% (92/112), 88 excluded | 92/112 = 82.1%, 88 excluded (exact match) | 112 | [74.0%, 88.1%] | cmd A; width-law sigma σ(τ)²=0.0066+0.0002τ |
| Hour-4 hold record (10% of bankroll) | $135.92, 21 trades, 19W–2L | $135.92, 21 trades, 19W–2L, min bankroll $100.00, stressed $131.83 (all exact) | 21 | win rate 19/21 = 90.5% [71.1%, 97.3%] | cmd B; params from .cache/strategy_lab/leaderboard.json |
| Hour-4 hold, flat $50 | $264.30, peak $292 | $264.30, peak $292.01 (exact) | 21 | same trades as above | cmd B |
| First-signal flat-$50 record | $321.53, 28 trades, 26W–2L | $321.53, 28 trades, 26W–2L, stressed $300.31 (all exact) | 28 | win rate 26/28 = 92.9% [77.4%, 98.0%] | cmd B |
| Win rate (hour-4 hold) | 90.5% (implied 19/21) | 19/21 = 90.5% | 21 | [71.1%, 97.3%] | cmd B |
| Win rate (first-signal) | 92.9% (implied 26/28) | 26/28 = 92.9% | 28 | [77.4%, 98.0%] | cmd B |
| 8 late-clarifier entries went 8/8 | 8/8 | 8/8, +$108.14 (exact; `fresh_only=1`) | 8 | [67.6%, 100%] | cmd B |
| Sat out 37 of 58 test days (hour-4) | 37/58 | 21 traded days → 37/58 (exact) | 58 | — (count, not a rate claim) | cmd B |
| 30 of 58 never qualify (first-signal) | 30/58 | 28 traded days → 30/58 (exact) | 58 | — | cmd B |
| 9:28–9:29 futures leg 13 of 13 | 13/13 | BLOCKED — 13-day minute history not in repo caches | 13 | [77.2%, 100%] (arithmetic on claimed 13/13) | results.tex states it "cannot be backtested further" |
| Quirk days safe under v1.2 | 4 of 12 | 4/12 (exact) | 12 | [13.8%, 60.9%] | cmd C |
| Committed acc baseline h0 (n=100 test) | 80.9% | 55/68 = 80.9% (exact; Brier 0.1785 exact) | 68 | [70.0%, 88.5%] | cmd D |
| Committed acc v1.2 h0 | 81.5% | 52/64 = 81.2% (Brier 0.1746 vs 0.1741 claimed) | 64 | [70.0%, 88.9%] | cmd D |
| Committed acc v1.3 h0 | 81.9% | 59/73 = 80.8% (Brier 0.1660 exact) | 73 | [70.3%, 88.2%] | cmd D |
| Committed acc v1.3 h4 | 84.2% | 64/76 = 84.2% (exact; Brier 0.1578 vs 0.1581) | 76 | [74.4%, 90.7%] | cmd D |
| Committed acc h9 (production = v1.2 late) | 94.2% | 82/87 = 94.3% (Brier 0.0696 vs 0.0708 claimed) | 87 | [87.2%, 97.5%] | cmd D |

Reproduction notes, stated plainly:

- The midnight ladder rung (145/200) and the confident-days split (92/112,
  88 excluded) reproduce **bit-for-bit** with the frozen core
  (a0 = 0.0092, k = 0.767, width-law sigma) on the 200-day slice.
- The 04:00/06:00/07:00/09:00 rungs recompute 1–2 days below the claimed
  counts (153 vs 154, 163 vs "82%", 168 vs "85%", 178 vs "90%"). The
  original figures came from an unretained script (figures/manifest.json:
  "Producer script not retained... No vector regeneration possible") and the
  dataset cache has since been rebuilt against live Yahoo bars. Every
  discrepancy is ≤ 1.0 accuracy point and deep inside the CI of either count.
- All five strategy-record claims ($135.92 / $131.83 / $264.30 / $321.53 /
  $300.31, 21 and 28 trades, 19W–2L and 26W–2L, 8/8, 37/58, 30/58)
  reproduce **exactly** from `.cache/strategy_days.json` with the leaderboard
  params. The two win-rate CIs are wide ([71%, 97%] and [77%, 98%]): with
  n ≤ 28 the record is consistent with a true win rate as low as ~71–77%.
- BLOCKED (cannot be recomputed from any repo data, per the honesty rule):
  the 9:29 minute-level rung (n=18), the 96.3% ceiling (n=81), and the
  13/13 futures leg. For these the CI is arithmetic on the stated count
  (which is uniquely determined by the stated percentage and n) and is
  labeled as such above. The 9:29 and ceiling CIs are wide enough
  ([74%, 99%] and [90%, 99%]) that the paper's "~94%" and "96.3%" wording
  should not be read as precise to the point.

## 2. Exact commands and outputs

Cmd A — accuracy ladder + confident split, 200-day window (frozen core):

```
python3 -c "
import json, math
from backtest import dataset
rows = dataset.load()
dates = [r['date'] for r in rows]
w = rows[dates.index('2025-09-09'):dates.index('2026-07-13')+1]   # len 200
def phi(z): return 0.5*(1+math.erf(z/math.sqrt(2)))
a0, k = 0.0092, 0.767
wl = lambda h: math.sqrt(0.0066 + 0.0002*(570-60*h))
for h in (0,4,6,7,9):
    n=hit=0
    for r in w:
        if h not in r['es']: continue
        n+=1; hit += ((a0+k*r['es'][h])>0)==(r['off']>0)
    print(h, hit, n)
ch=cn=0
for r in w:
    p = phi((a0+k*r['es'][0])/wl(0))
    if max(p,1-p) < 0.65: continue
    cn+=1; ch += (p>0.5)==(r['off']>0)
print('conf', ch, cn, 'excluded', 200-cn)"
```

Output: `0 145 200 / 4 153 200 / 6 163 200 / 7 168 200 / 9 178 200 /
conf 92 112 excluded 88`.

Cmd B — strategy records (params verbatim from
`.cache/strategy_lab/leaderboard.json`):

```
python3 -c "
from strategy import data, sim
days = data.build(); tr, te = data.split(days)
ex = {'half_spread':0.01,'impact_per_100':0.001}
fs = {'h_start':4,'h_end':9,'edge':0.05,'gate':0.7,'signal':'model','stake_abs':50,**ex}
h4c = {'hour':4,'edge':0.05,'gate':0.6,'signal':'model','maker':0,'bet_frac':0.1,**ex}
h4f = {'hour':4,'edge':0.05,'gate':0.6,'signal':'model','stake_abs':50,**ex}
for name, fam, prm in (('first_signal
$50',    'first_signal', fs),
                       ('hold h4 10%','hold', h4c), ('hold h4 $50','hold', h4f)):
    r = sim.run(fam, te, dict(prm)); m = r['metrics']
    wins = sum(1 for t in r['trades'] if t['pnl']>0)
    print(name, m['final_bankroll'], m['n_trades'], wins, m.get('min_bankroll'))"
```

Output: `first_signal $50 321.53 28 26 | hold h4 10% 135.92 21 19 min 100.0
| hold h4 $50 264.3 21 19, peak 292.01`. Stressed (half_spread 0.02,
impact 0.002): first_signal 300.31, hold-10% 131.83. `fresh_only=1` slice
of first_signal: 8 trades, 8 wins, +$108.14.

Cmd C — quirk safety, v1.2 fitted on the 200-day train half:
`quirk_report(ModelV12().fit(w[:100]), w)` → 4/12 safe (safe days
2025-09-12, 2026-06-01, 2026-06-22, 2026-07-10).

Cmd D — calibration table, test half of the 200-day window (n=100),
`backtest.run.metrics` per model/hour:

```
baseline h0 Brier 0.1785 commAcc 55/68=80.9% oc80 6 coinflip 32%
v1.2     h0 Brier 0.1746 commAcc 52/64=81.2% oc80 3 coinflip 36%
v1.3     h0 Brier 0.1660 commAcc 59/73=80.8% oc80 5 coinflip 27%
v1.3     h4 Brier 0.1578 commAcc 64/76=84.2% coinflip 24%
baseline h9 Brier 0.0667 commAcc 85/90=94.4% oc80 3
v1.2     h9 Brier 0.0696 commAcc 82/87=94.3% oc80 0
v1.3     h9 Brier 0.0690 commAcc 84/91=92.3% oc80 2
```

## 3. Bootstrap bands (deliverable 2)

Method (`strategy/bootstrap.py`, stdlib only): per test day, extract a
stake-independent contract (entry side, entry-minute market token price,
resolution outcome, day volume) from one canonical `sim.run`; entry
decisions in `hold`/`first_signal` never read the stake, so contracts are
valid under any staking rule. Resample the 58 test-day contracts **with
replacement** (B = 10,000, seed 20260719, `random.Random`) and replay each
sequence through the exact execution model (1c half-spread, 0.1%/$100
impact, Fee Structure V2 taker fee, 1%-of-volume liquidity cap, $1k
volume gate, no leverage, ruin below $1). Before any resampling the
identity ordering is asserted to match `sim.run`'s final bankroll to the
cent (all three configs pass).

End-value percentiles over 10,000 resamples ($100 start):

| Strategy | Actual end | 5th | Median | 95th |
|---|---|---|---|---|
| first_signal, flat $50 (champion) | $321.53 | $95.60 | $326.60 | $491.64 |
| hold hour-4, 10% of bankroll | $135.92 | $94.87 | $136.67 | $191.28 |
| hold hour-4, flat $50 (extra, for the $264.30 claim) | $264.30 | −$0.08 | $267.38 | $432.43 |

Readings: both headline records sit within ~2% of their bootstrap medians
(no ordering luck). Both 5th percentiles fall just below the $100 start —
about one resample in twenty ends at a small loss. Flat $50 from a $100
start is the fragile one: its 5th percentile is ruin (−$0.08; stakes are
bankroll-capped, so a loss streak burns to ~$0 plus fees), which is the
paper's own sequence-risk point ("losses-first busts on day two")
quantified. Full per-day arrays: appendix below and
`.cache/bootstrap_bands.json` (57 KB; also carries hold_h4_flat50).

Command: `python3 -c "from strategy import bootstrap; bootstrap.main()"`
(1.9 s). Output reproduced verbatim in the table above.

## 4. Reliability diagram + Brier (deliverable 3)

Prediction time: **9:00 ET** (hour 9 of the hourly dataset — it has 100
test days; 9:29 exists only as the unretained 18-day minute sample, so its
Brier is BLOCKED). Model: `ModelProd` (production: v1.3 before 5:00, v1.2
after — at 9:00 this is v1.2) fitted on the 200-day window's first 100
days, evaluated on the held-out 100 (2026-02-12..2026-07-13).

**Brier at 9:00, test half: 0.0696** (ModelProd). Same-split references:
baseline 0.0667, v1.3 0.0690. (The paper's Table 2 quotes 0.0708 at h9
from the pre-rebuild dataset; drift 0.0012.)

Decile bins (predicted P(up) → observed UP frequency, 95% Wilson):

```
[0.0,0.1): n=24 up= 0 obs=0.00 [0.00,0.14]
[0.1,0.2): n=10 up= 0 obs=0.00 [0.00,0.28]
[0.2,0.3): n= 6 up= 2 obs=0.33 [0.10,0.70]
[0.3,0.4): n= 3 up= 2 obs=0.67 [0.21,0.94]
[0.4,0.5): n= 4 up= 1 obs=0.25 [0.05,0.70]
[0.5,0.6): n= 5 up= 4 obs=0.80 [0.38,0.96]
[0.6,0.7): n= 4 up= 4 obs=1.00 [0.51,1.00]
[0.7,0.8): n=10 up= 8 obs=0.80 [0.49,0.94]
[0.8,0.9): n=10 up=10 obs=1.00 [0.72,1.00]
[0.9,1.0): n=24 up=24 obs=1.00 [0.86,1.00]
```

The distribution is bimodal — 48 of 100 days land in the two extreme bins
and go 24/24 down-calls and 24/24 up-calls correct; the middle bins are
thin (3–6 days) and their Wilson intervals straddle the diagonal, so the
diagram shows no detectable miscalibration at this n.

Command: `python3 -c "from backtest.plot import reliability_diagram;
print(reliability_diagram())"` → `('plots/reliability_diagram.png',
0.06963178028376711, 100)`.

## 5. Figures and manifest

- `plots/reliability_diagram.png` + `.pdf` — new; producer
  `backtest/plot.py::reliability_diagram` (matplotlib confined to the
  plotting helper, repo palette).
- `plots/strategy_bankroll_50_band.png` + `.pdf` — new; producer
  `strategy/plot.py::bankroll_band` over `strategy/bootstrap.py` bands.
- `figures/manifest.json` — two entries appended, status "made", captions
  carrying the real numbers above.

## Appendix — per-day bootstrap band arrays

Day index i = bankroll after the i-th day of the resampled 58-day
sequence; calendar dates listed first are the actual test-day dates
(used as the x-axis of the band figure).
