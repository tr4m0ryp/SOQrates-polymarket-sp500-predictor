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
3. **NOII-vs-print deviation on real days** (vision "In scope", previously
   dropped from this list). The sweep result points here: if coverage is not
   the constraint, indicative-vs-print accuracy is. `spx/replica/core/
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

---

# Autonomous Refinement (2026-08-13)

Two audits ran against §1-§5. The completeness audit's findings are folded in
above. The adversarial audit **refuted the central claim**, and its verdicts
are recorded here rather than quietly edited away, because §1.1 was published
to the repo and to the user before this section existed.

## The headline claim is withdrawn

**§1.1 "replica 5/12 beats futures 2/12" is not supported.** Three
independent defeaters, each verified in the main thread before acceptance.

**1. Lookahead. The replica is scored with the answer in hand.**
`IMB_WINDOW` runs to 09:33 and `tools/stage3_eval.py` takes the *last*
snapshot carrying `pred_open`, with no time bound. Verified on 2026-07-10:
**69.3% of index weight has its last `pred_open` timestamped at or after
09:30:00, max +179s.** After the open, `pred_open` is no longer an
indicative: it equals the realized cross (median error 0.00 bp). The futures
arm is scored at 09:00. This is not a like-for-like comparison; it is a
partial oracle against a 30-minutes-early forecast.

**2. The score is below a constant baseline.** Of the 12 days, 7 opened down
and 5 up. **Always-predict-down scores 7/12; the replica scores 5/12;
always-up scores 5/12.** The replica makes 6 up-calls against 5 up days, so a
permutation null with fixed marginals gives E[hits]=6.0 and P(hits>=5)=0.88.
5/12 is not evidence of skill in any direction.

**3. The futures baseline is circular.** `spx/config.py` defines QUIRK_DAYS
as "ES held direction, official printed opposite/tiny" - days selected
*because futures failed on them*. Scoring futures there and reporting 2/12 is
a tautology, not a baseline. Inverting the futures arm on the same days
scores 10/12 (v1.3) and 11/12 (v1.2, prod). I should have caught this from
the constant's own comment.

**§1.1's zero-overlap claim is also withdrawn.** With 5 and 2 correct days
placed at random over 12, P(zero overlap) = C(7,2)/C(12,2) = 0.32 (0.58
against prod). A one-in-three coincidence cannot carry a complementarity
claim, and the McNemar p-values in the same paragraph already said the arms
were not separated.

## The finding that replaces it

An oracle given every realized opening cross price for all constituents,
weighted and referenced to each stock's own auction `ref_price`, scores
**3/12** on these days, with **corr(oracle gap, official gap) = -0.28** and
MAE 0.127% against a mean |official| of 0.0455%. Perfect constituent auction
knowledge is *worse than predicting zero*.

Meanwhile corr(ES@09:00, official) = +0.957 over all 464 days with 89% sign
agreement, so the ground truth is sane in general. The decoupling is specific
to the selected days.

**Therefore the stage-3 replica family has no reachable target on this day
set, and the ceiling is below chance.** The 5/12 was never a floor to
improve on. This is the run's real result and it is a negative one: the
project's identified path past the futures ceiling does not exist in the form
the paper proposes. Why the official print decouples from constituent auction
prices on these days (index-calculation timing, the divisor, or Yahoo's
"open" not being the first index tick) is a better research question than the
replica, and determines whether stage 3 has a target at all.

## Fifth defect, still live: the ground-truth cross-check passes vacuously

`spx/data/ground_truth.py` fetches stooq, which now serves a JavaScript
proof-of-work bot wall. Verified: `stooq_daily()` returns **0 rows**, so
`audit()` intersects an empty set, returns `[]`, and `cmd_ground-truth`
prints "yahoo and stooq agree on every official open". The check guarding
the target of every arm has been passing because it compares nothing. Four
of the twelve quirk targets are also smaller than the repo's own 0.75-point
ground-truth tolerance (2026-06-22 is 0.14 pt), so their sign is not
resolvable at the precision the project itself demands.

## Other confirmed defects in §2's framing

Defect 1 (weights headers) was **loud and fail-closed**, not silent
corruption; §2's blanket "none raised an error" is wrong for that entry.

Additional look-ahead not covered by the timing-model split: `weights.load()`
scrapes *today's* index membership with no as-of date and applies it to
2025-09-12, up to 11 months of survivorship and weight look-ahead. Weight
jitter of 5-20% moves the score between 5 and 6 of 12, so the headline sat
inside weight-error noise regardless.

The Monte Carlo is **~3x overconfident**: z = (official - mean)/sigma has RMS
3.14 against an expected 1.0, with |z|>2 on 5 of 12 days. `fused_p_up`
inverse-variance-blends on that sigma, so fusion would hand the replica
almost all the weight precisely because it is miscalibrated. The §5 fusion
kill criterion would fire for reasons unrelated to complementarity.

## Revised work order

1. **Do not revise the paper to claim the replica works.** The honest paper
   delta is the negative result plus the five defects, and an explicit
   retraction of the projected "majority called".
2. Thread a hard `as_of` cutoff through `snapshots()` and make it the only
   supported evaluation path. Nothing measured before that is interpretable.
3. Retire hand-picked QUIRK_DAYS as an evaluation set; score both arms on all
   232 test-half days and report the sign-disagreement stratum at its full
   n=22 with a stated rule.
4. Replace sign-of-mean scoring on 0.14-point targets with Brier/log score,
   and implement the ground-truth exclusion CLAUDE.md mandates.
5. Fix or replace the stooq cross-check.
6. Recalibrate the Monte Carlo before any fusion work.
7. Investigate the -0.28 decoupling. This is the publishable question.

Incidental: `montecarlo.simulate` calls `cons.index(c)` inside the
2000-scenario loop (~100M dataclass comparisons/day); hoisting the index map
gives ~50x speedup with bit-identical output.
