# Technical design: complete-missing-gaps-spx-open

Status: research stage complete 2026-08-13. Produced by direct measurement in
the main thread rather than by `/flow:research`, because the first real
Databento pull exposed four defects that would have invalidated any design
reasoned on top of the pre-existing code. Every number here comes from a
command that was run; nothing is projected.

Vision: `notes/complete-missing-gaps-spx-open.md`
Evidence: `.claude/godmode/complete-missing-gaps-spx-open/recon.md`,
`.cache/stage3_eval.json`, `.cache/futures_baseline.json`

## 1. What was measured

### 1.1 Headline: the replica is complementary to futures, not better than it

Out of sample. Timing fitted on 17 ordinary days, evaluated on the 12 quirk
days it never saw. Direction-only scoring on both arms, identical dates.

| Arm | Quirk days called |
|---|---|
| Auction replica | 5/12 |
| Futures v1.3 | 2/12 |
| Futures production | 1/12 |

The measured 2/12 for v1.3 reproduces the figure the paper's appendix states,
which validates the scoring criterion.

Paired analysis is the load-bearing result. Against v1.3: replica-only 5,
futures-only 2, **both correct 0**, neither 5. Against production:
replica-only 5, futures-only 1, both 0, neither 6. Exact McNemar
p=0.453 and p=0.219 respectively, so **the improvement is not statistically
significant at n=12**.

The zero-overlap cell is the finding. The two signals are correct on disjoint
sets of days, so the defensible claim is complementarity, and the design
implication is fusion (`spx/replica/pipeline.py:fused_p_up`) rather than
replacement. A "the replica beats futures" claim is not supported; a "the
replica sees days futures structurally cannot" claim is, subject to n.

### 1.2 Backfill economics (answers vision question 1)

$0.2047 per day measured via the free `metadata.get_cost` endpoint, so the
agreed $50 cap affords roughly 244 trading days. 29 days pulled for $7.66.
Validation-window size is therefore a statistical question, not a budget one.

### 1.3 Print timing (answers vision question 2)

11,460 real cross prints over 23 days: median 1.02s after 9:30, p90 1.58s,
92.6% within 2s, **47.0% within the 1.0s photo moment the model uses**. The
p_live estimator is Laplace-smoothed as `(hits + 0.5)/(n + 1)`, so one day
caps any ticker at 0.75 and a stable per-name fit needs 10+ days. Fit on
ordinary days and score on quirk days; sharing days leaks the answer.

The photo moment is the largest identified lever: at 2.0s the replica would
see 92.6% of constituents instead of 47%. An in-sample sweep is underway and
must not be reported as a result, because tuning a parameter on the same 12
days it is scored on is the selection bias `spx/backtest/reality_check.py`
exists to catch. Any chosen photo moment needs out-of-sample confirmation.

## 2. Four defects fixed (all silent-corruption class, none raised an error)

1. **Weights host headers.** Slickcharts 403s a bare `Mozilla/5.0`;
   nasdaqtrader 406s an html-only `Accept`. `weights.load()` fell through to
   the iShares bot-wall and died on `StopIteration`. Nothing downstream can
   run without weights. Fixed with one header set both hosts serve.
2. **NYSE indicative blanked.** `_px(0)` returned `0.0` rather than `None`,
   so `_indicative()` short-circuited on NYSE Pillar's unpopulated
   `ind_match_price = 0` and never reached `cont_book_clr_price`. All 345
   NYSE constituents silently had no predicted open: 161 of 501 tickers
   usable. Fixed: 501 of 501.
3. **Split-adjusted prior closes.** Yahoo history is split-adjusted,
   Databento prices are raw. Every historical gap was wrong by the cumulative
   split factor (NFLX +899%, BKNG +2383%, index gaps to +13.4%). Fixed by
   using the auction's own contemporaneous `ref_price`, which also removed a
   501-request sequential fetch from stage-3.
4. **Opening cross misidentified.** `cross_print_map` took the earliest trade
   in a window that opens at 9:29:55, so liquid names got pre-open odd lots:
   AAPL 20 shares instead of a 404,032-share cross. Roughly 10% of tickers
   had physically impossible negative print delays. Fixed by taking the
   largest trade; zero negative delays remain. The trades schema carries no
   cross flag (`flags` holds only F_LAST), so size is the discriminator.

Consequence for the paper: every stage-3 number this project produced before
2026-08-13 was computed with at least one of these active. The 5/12 above is
the first valid stage-3 measurement.

## 3. Environment state

Live and verified: `DATABENTO_API_KEY` (XNAS.ITCH + XNYS.PILLAR entitled),
Overleaf git token (project `6a5bf21b6022bf005e17893a`, slug `soqrates`,
clone verified), `LLM_API_KEY` (NVIDIA, 102 models, live inference verified).

Absent, parked per C7 with activation checklists owed: WRDS, IBKR, LSEG,
Massive. `FRED_API_KEY` also absent, so the macro calendar degrades to the
NFP first-Friday rule.

Two integration findings from verifying the LLM key: five of nine models in
`spx/news/eval/bench.py:SHORTLIST` no longer exist on NVIDIA, so the bench
list must be refreshed against the live catalogue; and reasoning models
return `content: None` when the token budget is consumed before an answer,
which the runner now raises as a named error instead of a `NoneType` crash.

## 4. Work remaining

Ordered by value, with the paper first because it currently asserts claims
the measurements supersede.

1. **Paper revision.** `sections/appendix/replica.tex` and `conclusion.tex`
   project "quirk days from 2 of 12 to a majority called" and label it
   explicitly as projection, not backtest. Replace with the measured 5/12,
   the paired zero-overlap result, the McNemar p-values, and an honest
   statement that n=12 cannot separate the arms. Add the four defects as a
   reproducibility note: they materially affect how prior numbers should be
   read. Sync to `soqrates`.
2. **Fusion arm.** The zero-overlap result makes fused replica+futures the
   obvious next measurement, and the code already exists.
3. **Photo-moment calibration**, out of sample, on days disjoint from both
   the timing fit and the quirk evaluation.
4. **Live morning loop**, replay-provable per C4, real-morning shakedown per
   C8 on the next trading day.
5. **News layer**, now unblocked: refresh the bench shortlist, run it, commit
   a provider, wire the bounded news voice into fusion.
6. **Hygiene**: ground-truth exclusion in code, bootstrap CLI subcommand,
   Alpaca decision, figure-producing scripts.

## 5. Kill criteria

- If the fusion arm does not beat both standalone arms on the same 12 days,
  the complementarity claim is decorative and the paper should say so.
- If the photo-moment sweep's out-of-sample confirmation fails to hold the
  in-sample gain, the 1.0s photo stays and the coverage ceiling is a stated
  limitation rather than a fixable parameter.
- If a larger quirk sample (more backfill, affordable under the cap) moves
  the replica toward the futures arms, the 5/12 was noise and the paper's
  claim reduces to "no evidence of improvement at n=12".
