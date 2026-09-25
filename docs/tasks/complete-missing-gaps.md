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
implication is fusion (`open_predictor/forecast/auction/pipeline.py:fused_p_up`) rather than
replacement. A "the replica beats futures" claim is not supported; a "the
replica sees days futures structurally cannot" claim is, subject to n.

### 1.2 Backfill economics (answers vision question 1)

$0.2047 per day measured via the free `metadata.get_cost` endpoint, so the
agreed $50 cap affords roughly 244 trading days. 29 full days pulled for $7.66 (the spend ledger also lists a 30th date, 2026-08-12, which failed with HTTP 403 as today's auction is unpublished; it is excluded from every analysis).
Validation-window size is therefore a statistical question, not a budget one.

### 1.3 Print timing (answers vision question 2)

Source: all 29 per-day digests, `.cache/databento/*/digest.json`, n=14,439
prints. Median 1.026s after 9:30, p90 1.595s, 92.6% within 2.0s, **46.2%
within the 1.0s photo moment the model uses**, zero negative. Do not
recompute from `.cache/print_delays.json`: that is the fit store and covers
only the 17 ordinary days (8,474 obs), a different population. The
p_live estimator is Laplace-smoothed as `(hits + 0.5)/(n + 1)`, so one day
caps any ticker at 0.75 and a stable per-name fit needs 10+ days. Fit on
ordinary days and score on quirk days; sharing days leaks the answer.

**The photo moment was hypothesised to be the largest lever. It is not, and
the sweep refutes it.** At 2.0s live index weight rises from 36.3% to 87.0%
as the coverage figures predict, but quirk calls stay at 5/12 and mean
absolute index error worsens from 6.79 to 11.14 bps. Newly included names
enter at indicative prices carrying preview noise (0.30% sigma NYSE), while
excluded names sit at prior close contributing zero, damping the estimate
toward the near-zero official gaps. Coverage is not the binding constraint,
so the remaining error is in the indicative prices themselves, not in how
many of them are used. This was an in-sample sweep and is reported as a
refutation, not as a tuning result.

At 5.0s: still 5/12, 11.33 bps, 88.2% live weight. The call count is
**identical at every photo moment tested** while live index weight ranges
from 36.3% to 88.2%. The replica's direction calls are therefore insensitive
to how much of the index it can see, which is itself a warning: a signal that
does not respond to more than doubling its input either is robust and
broad-based, or is being set by something other than the auction evidence.
Deciding which is a prerequisite for any claim built on the 5/12.

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
`open_predictor/forecast/news/eval/bench.py:SHORTLIST` no longer exist on NVIDIA, so the bench
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
3. **NOII-vs-print deviation on real days** (vision "In scope", previously
   dropped from this list). The sweep result points here: if coverage is not
   the constraint, indicative-vs-print accuracy is. `open_predictor/forecast/auction/core/
   deviation.py` has only ever run on 2019 ITCH samples.
4. **Evaluation refresh**: re-run `backtest`, `baselines` and
   `reality_check` with the replica arm included, per the vision's
   evaluation-refresh scope item.
5. **Context pack + open questions updated in the same pass** (C5). This was
   missing from an earlier draft of this list, which is exactly the failure
   C5 names.
6. **Two vision questions still unanswered and not deferred anywhere**: which
   remaining free news feeds (Truth Social, EDGAR 8-K, release endpoints) and
   FMP slots earn their maintenance cost, and how to re-derive Polymarket
   series id 10945 programmatically instead of hardcoding it.
7. **Live morning loop**, replay-provable per C4, real-morning shakedown per
   C8 on the next trading day.
8. **News layer**, now unblocked: refresh the bench shortlist, run it, commit
   a provider, wire the bounded news voice into fusion.
9. **Hygiene**: ground-truth exclusion in code, bootstrap CLI subcommand,
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
