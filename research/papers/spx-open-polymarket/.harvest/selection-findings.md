# Selection-bias correction for the strategy backtest (White's reality check)

Date: 2026-07-19. Script: `backtest/reality_check.py` (committed).
Run from repo root: `python3 -m backtest.reality_check`.

## Method

**White's reality check** (White 2000, Econometrica 68(5)) over the full
candidate family, with a **stationary bootstrap** (Politis & Romano 1994),
B = 10,000 draws, mean block length 5 days, on the 58-day test half
(2026-04-16..2026-07-14).

- **Family, size 15 (primary):** the exact 15 unique verified candidates
  the paper refers to. Provenance: the 28-agent verification workflow
  artifact (session `380c3a0d`, run `wf_89eb270d`,
  `~/.claude/projects/-Users-macbookpro-projects-trading-polymarket-stock/380c3a0d-*/workflows/wf_89eb270d-05c.json`,
  `result.candidates`) records 16 submissions that dedupe to 15 unique
  parameterizations (two differ only by an explicit engine-default key).
  This is not an approximation of the family — it is the recorded roster.
- **Extended family, size 17 (sensitivity):** the 15 plus the two
  candidates selected *after* the workflow and now headlined by the paper:
  `first_signal` (h4-9, edge .05, gate .70) and the `full_strategy`
  composite (same entry + px_max .95 + checkpoint exits). Selection in
  fact continued past the recorded 15, so the paper's abstract survivor is
  only covered by this run.
- **Per-day PnL reconstruction:** each candidate re-run through the actual
  engine (`strategy/sim.py` on `.cache/strategy_days.json`) on the test
  half at flat $100 research stakes (`bet_frac`/`stake_abs` stripped so
  units are comparable; `sizing="optimal"` kept where it is part of the
  strategy). Days skipped by the volume gate count as $0 days on the fixed
  58-day grid.
- **Test statistic:** V = max over candidates of sqrt(58) x (mean daily
  flat-stake PnL). Bootstrap draws resample day indices jointly across all
  candidates (cross-candidate correlation preserved); each candidate is
  centered at its own sample mean (White's least-favorable null, E[f]=0).
  Adjusted p = fraction of draws whose bootstrapped max >= observed V.
  Naive p = the same bootstrap applied to the best candidate alone
  (single-hypothesis test, no selection correction).

Reconstruction fidelity: the survivor's recorded compounding number
reproduces bit-for-bit ($100 -> $135.92, 21 trades, win .905, min $100.00),
and every candidate whose flat test PnL appears in the workflow verdicts
matches exactly (e.g. flow_flip -758.15 / -821.24 / -922.49, longshot
-504.47, takeprofit +67.73, convergence -74.58 / -75.57). No number below
is estimated or approximated.

## Results

| Family | Best candidate | Mean $/day (flat $100) | V | Naive p | RC-adjusted p |
|---|---|---|---|---|---|
| 15 recorded | hold h4, edge .05, gate .60 | 5.64 (total +327.01/58d) | 42.94 | 0.0255 | **0.3613** |
| 17 extended | full_strategy h4-9, gate .70, px_max .95 | 7.68 (total +445.27/58d) | 58.47 | 0.0230 | **0.2611** |

(first_signal alone: mean 7.60 $/day, total +441.01 — second-best in the
extended family by a hair.)

Seed stability (B=10,000 each): family-15 adjusted p = .359/.365/.360,
family-17 = .270/.268/.262 across seeds 1/7/12345; Monte-Carlo SE ~ .005.
The extended family's *lower* adjusted p is not an error: adding the two
late candidates raises the observed max more than it raises the bootstrap
null max (the three positive candidates are highly correlated — they trade
the same days).

**Verdict: not significant after selection.** The unadjusted test says
p ~ 0.02-0.03 ("significant at 5%"); once the best-of-family selection is
priced in, the adjusted p is 0.26-0.36. The test half cannot distinguish
the survivor's performance from the luck of the best of 15 (or 17) tries.
Note the correction is a *lower bound*: train-side grid searches touched
>100 parameter cells across iterations, and only the walked-forward
candidates are recorded; a family-wise correction over the true search
breadth would be weaker still. A Bonferroni binomial on the 19W-2L record
was NOT used: entry prices average ~0.80-0.90, so a no-edge bettor also
wins most trades — W-L is uninformative here and mean PnL is the honest
statistic.

## Sentences the paper can use

Correcting the survivor's test-half performance for the fact that it is the
best of 15 candidates, White's reality check (stationary bootstrap,
10,000 draws, mean block 5 days) gives an adjusted p of 0.36 against a
naive p of 0.03; including the two later-selected variants
(first-signal entry and the composite) the adjusted p is 0.26. Fifty-eight
test days are simply too few to separate a genuine edge of this size from
the luck of the best of fifteen tries, and we report the backtest as
promising but statistically unconfirmed. The economic magnitude
(~$5.6/day per $100 flat stake) is what a further out-of-sample live
period must confirm or refute; the multiplicity-adjusted evidence to date
does not yet do so.

## Exact commands and outputs

```
$ cd /Users/macbookpro/projects/trading/polymarket/stock
$ python3 -c "...sim.run('hold', test, {hour:4, edge:.05, gate:.6, signal:'model', bet_frac:.1, half_spread:.01, impact_per_100:.001})..."
days 115 train 57 test 58 2026-04-16 2026-07-14
survivor compound final_bankroll: 135.92 min: 100.0 trades: 21 win: 0.905

$ python3 -m backtest.reality_check
test half: 58 days 2026-04-16..2026-07-14  |  flat $100 stakes  |  B=10000 stationary bootstrap (mean block 5d, seed 20260719)

== recorded family (paper's 15): 15 candidates ==
 mean$/d   total$  candidate
    5.64   327.01  hold edge=0.05,gate=0.6,hour=4
    1.76   102.03  hold edge=0.08,gate=0.6,hour=4,maker=0
    1.17    67.73  takeprofit edge=0.07,gate=0.6,hour=4,tp=0.97
    0.65    37.75  hold edge=0.04,gate=0.65,hour=7,maker=1,maker_disc=0.03
   -1.08   -62.72  hold edge=0.05,gate=0.6,hour=5,maker=0
   -1.11   -64.64  longshot h_min=0,max_stake=10,p_min=0.3,px_max=0.12,sizing=optimal
   -1.29   -74.58  convergence edge=0.05,exit_h=9,gate=0.6,hold_ok=0,hour=5,margin=0.01,min_move=0.05
   -1.30   -75.57  convergence edge=0.08,exit_h=9,gate=0.6,hold_ok=1,hour=4,margin=0,min_move=0.05
   -1.44   -83.67  takeprofit edge=0.05,gate=0.6,hour=5,tp=0.95
   -1.44   -83.67  takeprofit edge=0.05,gate=0.6,hour=5,maker=0,tp=0.95
   -1.54   -89.49  hold edge=0.06,gate=0.6,hour=5,maker=0
   -8.70  -504.47  longshot h_min=0,max_stake=20,p_min=0.25,px_max=0.25,sizing=optimal
  -13.07  -758.15  flow_flip agree_min=0.55,flip_edge=0.15,flip_from=8,h0=1,min_lean=0.02
  -14.16  -821.24  flow_flip agree_min=0.55,flip_edge=0.1,flip_from=8,h0=1,min_lean=0.02
  -15.90  -922.49  flow_flip flip_edge=0.15,flip_from=8,h0=1
best: hold edge=0.05,gate=0.6,hour=4
  V = sqrt(58) * mean = 42.94
  naive (unadjusted) bootstrap p = 0.0255
  White reality-check adjusted p = 0.3613

== extended family (15 + later survivors): 17 candidates ==
 mean$/d   total$  candidate
    7.68   445.27  full_strategy edge=0.05,exit_thr=0.5,flip=1,gate=0.7,h_end=9,h_start=4,px_max=0.95
    7.60   441.01  first_signal edge=0.05,gate=0.7,h_end=9,h_start=4
    5.64   327.01  hold edge=0.05,gate=0.6,hour=4
    [... identical 12 rows as above ...]
best: full_strategy edge=0.05,exit_thr=0.5,flip=1,gate=0.7,h_end=9,h_start=4,px_max=0.95
  V = sqrt(58) * mean = 58.47
  naive (unadjusted) bootstrap p = 0.0230
  White reality-check adjusted p = 0.2611

$ python3 -c "...reality_check with seeds 1,7,12345..."
seed 1: family15 p_rc=0.3590 p_naive=0.0234 | family17 p_rc=0.2699 p_naive=0.0253
seed 7: family15 p_rc=0.3650 p_naive=0.0264 | family17 p_rc=0.2678 p_naive=0.0249
seed 12345: family15 p_rc=0.3599 p_naive=0.0222 | family17 p_rc=0.2624 p_naive=0.0251
```

Consistency cross-checks against independently recorded numbers: flat totals
at $100 stakes ~ 2x the $50-stake bankroll gains in the lab notes
(hold h4: 327.01 vs 2x164.30=328.60, first_signal: 441.01 vs 2x221.53=443.06;
small gaps = the 1%-of-volume liquidity cap binding differently at $100).
