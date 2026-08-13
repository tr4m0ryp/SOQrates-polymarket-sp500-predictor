# Per-Model Finetuning, Full Backtest, and Calibration -- Technical Design
# Started: 2026-08-13
# Source vision: notes/finetune-and-calibrate-models.md

## Brief

Tune each arm of the SPX open predictor, calibrate its confidence, wire the
validated auction replica into the Polymarket simulator, and run one honest
backtest with a per-day ledger covering traded and untraded days alike. The
objective is expected value against the market price, not accuracy against the
open (C7).

This doc resolves the 17 parked questions from the vision, and fills the two
invention slots (I1 uncallability detection, I2 sign-reliable confidence).

Standing empirical context, all measured on 2026-08-13 and recorded in
`.claude/godmode/complete-missing-gaps-spx-open/recon.md`:

- Replica calls 10/11 futures-disagreement days on a pre-registered holdout
  (p=0.006 exact binomial, best trivial baseline 6/11).
- Index reconstruction error is 0.129% (pre-open, split-correct closes, 17
  ordinary days); near-tie days move 0.046%. The error is ~3x the signal on
  that stratum. An earlier 0.101% figure circulated: that was the
  close-to-close daily-return reconstruction over 275 days, a different
  quantity, and it must not be used for the opening gap.
- The Monte Carlo is ~3x overconfident: z=(official-mean)/sigma has RMS 3.14
  against an expected 1.0.
- Liquidity caps a trade near $1,000 on a market doing $30-48k/day.

## Hypothesis & Kill Criteria

**H1 (decidability).** A target-side decidability score computed before 9:30
from auction microstructure separates callable from uncallable days better
than thresholding model confidence. Formally: at matched coverage, selective
error under the decidability rule is strictly lower than under `CONF_COMMIT`.

**H2 (calibration).** A one-parameter shrinkage of the replica's predicted
mean restores unit-RMS z-scores without degrading sign accuracy, and a
sizing rule built on the shrunk confidences outperforms one built on raw
confidences after fees.

**H3 (economic).** Adding the replica arm to the simulator increases total
return primarily by increasing the number of qualifying days, not by raising
per-trade edge (C11).

**Kill criteria, pre-registered.**

- **H1 dies** if the decidability score fails to separate accuracy between its
  top and bottom halves on held-out days by at least 15 percentage points, or
  if it fails to beat `CONF_COMMIT` on the risk-coverage curve at any coverage
  between 40% and 80%.
- **H2 dies** if shrinkage that fixes z-RMS costs more than 1 sign flip per 20
  days, i.e. if magnitude and sign are not separable after all.
- **H3 dies** if the replica arm adds fewer than 5 qualifying days per 100
  trading days, making the marginal return smaller than the data cost.
- **All three die** if the per-day ledger shows the existing $321 result does
  not survive replacing midpoint fills with a conservative spread assumption.
  That would mean the baseline itself is an artifact and everything built on
  it is moot.

Negative results are written up. If H1-H3 all fail, the paper reports a
validated open-prediction signal that could not be converted into a tradeable
edge, which is a publishable and useful finding.

## Recommended Technical Design

Five components, built in dependency order.

**1. Per-day ledger (the instrument).** One row per trading day in the
market-history window, traded or not: model probability per arm, fused
probability, market price at each decision checkpoint, edge, decidability
score, the rule that suppressed the trade if suppressed, realised outcome,
modelled PnL under two fill assumptions. This is built first because every
later claim is read off it, and because it is the artifact the paper needs.

**2. Decidability estimator (I1, Tier 1).** A pre-open estimate of the
target's own noise floor, used to abstain on days where the predicted move is
smaller than the reconstruction error. Keyed to the day's own coverage and
dispersion, not to the model's posterior. Specified in `## Formal Model`.

**3. Sign-preserving calibration (I2, Tier 1-B).** A single shrinkage
parameter fitted on tuning days that restores unit-RMS z-scores, leaving sign
untouched. One degree of freedom by design, because C10 budgets them.

**4. Replica arm in the simulator.** The auction signal enters `data.py` day
records as an additional probability series available from 09:20, fused with
futures by inverse variance using the *calibrated* sigma from (3).

**5. Sizing.** Edge-proportional below the liquidity ceiling, hard-capped
above it, with the fraction set by calibrated confidence from (3). Sequenced
strictly after calibration (C12).

## Natural Basis & Fidelity Gaps

The phenomenon is the formation of the official opening print from ~500
independent constituent auctions. The relevant "natural" systems here are the
exchange auction mechanisms themselves and the human traders who price them.

| System | Natural basis | Implemented faithfully | Divergence / under-implementation | Improvement implied |
|---|---|---|---|---|
| Our futures model (v1.2/v1.3) | Overnight information flow into a cash open | Gap attenuation, regime-scaled volatility | Treats the open as a smooth function of the overnight gap; the open is actually a discrete auction clearing event | Model the clearing event, not the drift (this is what stage 3 does) |
| Our auction replica | Per-stock auction clearing then index aggregation | Indicative prices, per-name print timing, imbalance | Assumes a single simultaneous "photo" moment; real prints stagger over ~200s and the index updates continuously | Continuous-time index assembly rather than a snapshot |
| `CONF_COMMIT` gate | A trader declining an unclear setup | Abstains when unsure | Conflates "I am unsure" with "this is unknowable"; a human trader distinguishes these instantly | Estimate target decidability separately from model confidence (I1) |
| Polymarket crowd | Aggregation of informed opinion | Prices overnight futures efficiently | Has no access to auction microstructure; prices the open from futures alone | Trade precisely where futures and auction disagree |
| Strategy sim execution | Filling against a real book | Spread and impact terms | Fills at archived **midpoints**, which no participant ever receives | Bound the optimism explicitly rather than assume it away |

**Cross-system pattern (the shared omission).** Every component models the
open as a *quantity to estimate* and none models it as a *quantity that may be
undefined at the resolution required*. The futures model, the replica, the
gate, and the market all assume the question has an answer. On roughly a third
of quirk days the official move is smaller than the project's own ground-truth
tolerance (0.75 index points; 2026-06-22 moved 0.14), so the question does not
have a resolvable answer at all. That shared omission is the binding
constraint and both inventions attack it.

## Related Work Map

| Work | What it does | Overlap with this design | How this differs |
|---|---|---|---|
| Franc, Prusa & Voracek 2021 (R1) | Proves cost-based, bounded-improvement and bounded-coverage reject models share one optimal strategy: Bayes classifier plus randomized Bayes selection on a *proper uncertainty score* | Our abstention rule is a selective classifier; the bounded-coverage form matches "trade N days per year at minimum loss rate" | They assume the label is well-defined and uncertainty is about the classifier. Our uncallable days have a label that is itself inside the measurement noise, so the proper uncertainty score must include a target-side term they do not model |
| Geifman & El-Yaniv 2019, SelectiveNet (R2) | Trains prediction and rejection jointly; notes existing mechanisms are "mostly based on a threshold over the prediction confidence of a pre-trained network" | That sentence describes `CONF_COMMIT` exactly | We cannot train jointly at n=22 days. We instead supply a *different score* rather than a better-trained threshold, which is cheaper in degrees of freedom |
| Bergna, Depeweg & Hernández-Lobato 2026 (R3) | Shows the epistemic/aleatoric split is **not identifiable** from the posterior predictive alone, and supplies the split via structural knowledge of the generating process | Directly licenses our approach: we cannot get decidability out of the model's own sigma | They obtain the split from a controlled synthetic generator. We obtain it from microstructure observables (coverage, per-name dispersion, tolerance), which is available in production and needs no synthetic prior |
| da Costa & Gebbie 2020 (R4) | Assesses trading strategies under combinatorially symmetric cross-validation and deflated/probabilistic Sharpe | Our C1/C9/C10 discipline | We adopt the deflation idea but our n is far too small for CSCV; we use pre-registration plus a counted degrees-of-freedom budget instead |
| Existing repo `reality_check.py` | White-style reality check for strategy selection bias | Same concern | Currently applied to strategy families only, not to the tuning decisions themselves. Extended here to cover the whole tuning campaign |

## Novel Contributions

**Tier 1 (invented from the domain).**

**N1: Target-side decidability estimation.** Abstain based on an estimate of
whether *today's answer is resolvable*, computed before the open from auction
observables, rather than on how confident the model is. The domain fact: the
official open is a discrete auction clearing event whose index-level
resolution is bounded by constituent coverage and indicative dispersion, both
observable at 09:29. No incumbent in the repo or in the selective-prediction
literature surveyed separates target decidability from model confidence in
this way, and R3 establishes that the separation cannot be recovered from the
predictive distribution alone. Falsifiable test: H1's risk-coverage
comparison against `CONF_COMMIT`.

**Tier 1-B (measured improvement on a named incumbent).**

**N2: Sign-preserving shrinkage calibration.** The replica is reliable in
sign (10/11) and inflated ~3x in magnitude, with z-RMS 3.14. Standard
probability calibration (Platt, isotonic) recalibrates the probability and
discards that structure; at n=22 it also spends far more degrees of freedom
than the data supports. A single shrinkage parameter fitted to restore unit
z-RMS corrects the defect with one degree of freedom and provably cannot flip
a sign. Beats: isotonic and Platt calibration as baseline arms, on
post-calibration Brier and on sign retention.

**Tier 2 (integration, no measured delta claimed).** The per-day ledger, the
replica-into-simulator wiring, the sizing rule below the liquidity cap, and
the stratified tuning protocol are recombination of known parts.

**Honestly incremental / borrowed unchanged:** inverse-variance fusion,
White's reality check, fractional-Kelly-style sizing, the existing execution
model's spread and impact terms.

## Improvement Targets

| Incumbent | What it does | Its limits | What our setting needs | Delta we build | Baseline arm |
|---|---|---|---|---|---|
| `CONF_COMMIT = 0.65` gate | Abstains when max(p,1-p) < 0.65 | Thresholds model confidence only; structurally cannot express "the target is unresolvable today"; single global constant, never refit | Abstention keyed to whether the day is decidable | N1 decidability score | `CONF_COMMIT` at matched coverage, on the risk-coverage curve |
| Monte Carlo posterior sigma | Supplies uncertainty to fusion and sizing | Measured z-RMS 3.14, so ~3x overconfident; feeding it to inverse-variance fusion hands the replica most of the weight *because* it is miscalibrated | Confidence that means what it says | N2 shrinkage | Raw sigma, plus Platt and isotonic calibration |
| Existing strategy sim | Model-vs-market rules on 21 trades | No auction arm; fills at book midpoints; abstentions unrecorded | Replica arm, honest fills, full ledger | Components 1 and 4 | The current sim, rerun unchanged |

## Formal Model

**Symbols.**

| Symbol | Meaning |
|---|---|
| `g` | index opening gap, percent of prior close |
| `ĝ` | replica point estimate of `g` |
| `w_i` | index weight of constituent `i` |
| `c` | covered weight fraction at the decision time |
| `s_i` | indicative-vs-print dispersion for name `i` (measured 16-17 bp) |
| `σ_r` | index-level reconstruction error |
| `σ_m` | Monte Carlo posterior sigma |
| `λ` | shrinkage parameter (I2) |
| `τ` | ground-truth tolerance, 0.75 index points |
| `D` | decidability score (I1) |
| `k` | decidability threshold |

**N1, decidability.** The index-level reconstruction error from independent
per-name errors is

    σ_r² ≈ Σ_i w_i² s_i²  +  (1 - c)² σ_stale²

The first term is per-name preview noise attenuated by weight concentration
(measured Σ w_i² = 0.02008, so the measured 20.2 bp median per-name error
contributes 2.9 bp); the second is the contribution of uncovered weight held
at prior close. Measured total is 12.9 bp, 4.5x the first term, and it does
not fall when realised prices replace indicatives (F4). The residual is
therefore localised in weights and coverage, not in the auction data.

Decidability is the ratio of predicted signal to the day's own noise floor,
with the ground-truth tolerance as a hard floor:

    D = |ĝ| / max(σ_r, τ / P_prev)

where `P_prev` converts the tolerance into percent. **Abstain iff D < k.**

The critical property: `D` does not contain `σ_m`. A model can be arbitrarily
confident and still be predicting a quantity below its own resolution, which
is precisely the 2026-01-29 failure (replica +0.4588% against an official
-0.0041%, on a day whose true move was 0.3 index points).

*Derived expectation.* If `D` measures what it claims, accuracy should rise
monotonically with `D` and approach the ordinary-day rate (17/17 observed) for
`D >> 1`, while approaching 50% as `D -> 0`. A predicted curve, not a bare
A/B: the shape is the test. Cost: O(n) per day over constituents, negligible.

**N2, shrinkage.** Choose `λ` minimising the deviation of standardised
residuals from unit variance on tuning days:

    λ* = argmin_λ ( RMS_d[ (g_d - λ ĝ_d) / (λ σ_m,d) ] - 1 )²

Since `λ > 0`, `sign(λ ĝ) = sign(ĝ)` identically, so no sign can flip: the
mechanism is sign-preserving by construction rather than by tuning. Expected
`λ ≈ 1/3` from the measured z-RMS of 3.14. One free parameter. Cost O(1).

*Tradeoff surface.* `λ` trades magnitude fidelity against confidence
calibration. Smaller `λ` shrinks predictions toward zero, which lowers stated
confidence and therefore stake size; the optimum is where stated confidence
matches realised frequency, not where PnL is maximised (C9 forbids the
latter).

## Evaluation Plan

**Minimal falsifying experiment, scheduled first.** Compute `D` on the 29
cached days and check whether accuracy separates between the top and bottom
halves by `D`. This uses data already on disk, costs nothing, and kills H1 in
an afternoon if the score is inert. Everything else is gated on it.

**Testbed versus product.** The testbed is the ledger plus the two scoring
functions, over cached days. The product is the live morning loop. They are
built separately and the testbed first; conflating them is what deferred the
live path since July.

**Baselines.** For H1: `CONF_COMMIT` (current), random abstention at matched
coverage, always-trade, and the naive-but-hard baseline of abstaining on small
|ES gap| alone. For H2: raw sigma, Platt scaling, isotonic regression. For H3:
the existing pre-replica simulator, rerun unchanged.

**Instrument.** The per-day ledger. It does not exist and building it is part
of the contribution, so it is build phase 1, not an afterthought.

**Metrics.** Risk-coverage curves with selective error at fixed coverage
(the standard instrument from R1/R2); Brier and z-RMS for calibration; total
and risk-adjusted return, plus qualifying-day count, for economics. Variance
via the existing day-resampled bootstrap (B=10,000). No point estimate is
reported without its interval.

**Ablations.** One per mechanism: `D` with the tolerance floor removed; `D`
with the coverage term removed; shrinkage with `λ` fixed at 1.

**Ground truth.** Yahoo `^GSPC` daily open, which was verified on 2026-08-13
to equal the 9:30 one-minute bar open to the cent. The stooq cross-check is
currently vacuous (0 rows behind a bot wall) and must be repaired or replaced
before any result is final; until then ground truth rests on a single source
and the doc says so.

**Statistical discipline.** Tuning and evaluation sets declared before any
sweep (C1). Outcome-informed decisions counted against an explicit budget
(C10). Every reported comparison pre-registered in the same form as the
2026-08-13 holdout test, which is the only number from that session that
survived.

## Decisions

### T1: Tuning/evaluation split
**Decision:** Chronological split with a frozen final test set. Tuning on the
earlier portion, evaluation on the later, and a final holdout never touched
until the protocol is written down. Stratified reporting within each (C5).
**Why:** Chronological matches the repo's existing convention and respects
the temporal structure; random splits leak regime information. CSCV (R4) is
unusable at this n.
**Alternatives rejected:** k-fold (leaks through repeated peeking when a human
picks the next sweep); random split (regime leakage).
**Confidence:** high

### T2: Days needed per arm
**Decision:** Timing model 10+ days minimum (measured: Laplace smoothing caps
p_live at 0.75 with one day). Decidability score needs ~50 days spanning both
strata. Shrinkage needs ~30 with variance in |g|. Futures arms already have
464 days.
**Why:** Derived from the smoothing arithmetic and from the observed
instability of 12-day results.
**Confidence:** medium

### T3: Which parameters are genuinely free
**Decision:** Free: `λ` (shrinkage), `k` (decidability threshold), fusion
weights. Fixed by data, not tuned: photo moment (swept 1.0-5.0s, calls
invariant at 5/12, so it carries no information), `PREVIEW_SIGMA` (measurable
directly from indicative-vs-print), venue priors (superseded by fitted
delays).
**Why:** The photo sweep is the strongest evidence: a parameter whose full
range produces identical calls is not a free parameter, it is inert.
**Confidence:** high

### T4: Calibration technique at small n
**Decision:** One-parameter shrinkage (N2). No isotonic, no Platt as the
production choice; both retained as baseline arms only.
**Why:** Isotonic has effective complexity growing with n and will overfit at
n=22-50; Platt fits two parameters and does not exploit the known
sign/magnitude asymmetry. Shrinkage spends one degree of freedom on a defect
that is already measured.
**Confidence:** high

### T5: Fusing arms correct on disjoint days
**Decision:** Inverse-variance fusion on *calibrated* sigmas, with the
replica's sigma taken post-shrinkage.
**Why:** The disjointness observed on 2026-08-13 was not significant
(P(zero overlap)=0.32 by chance), so no exotic combiner is justified. But
fusing on raw sigma would hand the replica most of the weight because it is
miscalibrated, which is the failure C12 exists to prevent.
**Alternatives rejected:** learned stacking (no data to fit it); winner-take-
all by regime (that is what the decidability score already does, better).
**Confidence:** medium

### T6: What "uncallable" means operationally
**Decision:** `D < k`, per the formal model. Decided pre-open from coverage,
dispersion and the tolerance floor.
**Confidence:** medium, pending the minimal falsifying experiment

### T7: Reduced universe versus CRSP weights
**Decision:** CRSP via WRDS is the gating dependency for the near-tie stratum;
the top-N reduction is **not** a substitute and was withdrawn after failing
its holdout. Build the WRDS fetcher; do not revisit top-N without a new
mechanism.
**Why:** Reconstruction error is 0.101% with the best available closes and
must reach ~0.02% for near-tie days. The residual localises in weights, and
scraped percentages cannot get there in principle.
**Confidence:** high

### T8: Reporting a backtest whose day set came from an in-period rule
**Decision:** Report the full-calendar result as primary and the
disagreement-stratum result as a secondary, clearly labelled as conditioned on
a rule derived in-period. Never report the stratum alone as a headline.
**Confidence:** high

### T9: How much auction history to buy
**Decision:** ~190 days, stratified: all rule-derived disagreement days in the
period plus a matched random sample of ordinary days. About $40, inside the
existing cap.
**Why:** Marginal value of ordinary days past ~100 is low (already 17/17);
marginal value of disagreement days is high and they are rare.
**Confidence:** medium

### T10: Live path requirements
**Decision:** The live loop needs a hard `as_of` cutoff enforced in
`snapshots()` (not merely in the request window), per-dependency health
checks, and a fail-closed default that abstains when any input is stale.
**Why:** On 2026-08-13 the weights source began returning 403 and the chain
died on a `StopIteration` from a CSV parser. In production that is a silent
outage on a trading morning.
**Confidence:** high

### T11: Silently-failing dependencies
**Decision:** Three known: index weights (403/406 on header policy change),
the stooq ground-truth cross-check (returns 0 rows, audit passes vacuously),
and vendor entitlement per slice. Each gets an explicit liveness assertion
that fails loudly.
**Confidence:** high

### T12: Polymarket history depth
**Decision:** Treat ~115 days as the working assumption and re-fetch to
confirm; the strategy backtest lives in the intersection of market history,
model dataset and auction data, so the binding constraint is market history.
**Confidence:** low, pending re-fetch

### T13: Midpoint fills
**Decision:** Report every economic result under two fill assumptions:
archived midpoint (optimistic, comparable to the paper's $321) and
midpoint-plus-half-spread against us (conservative). The gap between them is
the honest uncertainty band.
**Why:** Fills were never observed, only modelled. Bounding the optimism is
cheaper and more defensible than trying to reconstruct a book.
**Confidence:** high

### T14: Replica into the simulator
**Decision:** The replica enters as an additional probability series available
from 09:20 onward, fused per T5. Days before auction data exists carry the
futures-only probability, so the ledger spans the full market-history window.
**Confidence:** high

### T15: Sizing rule
**Decision:** Edge-proportional with a fractional-Kelly cap, hard-limited by
the liquidity ceiling, driven by post-shrinkage confidence. Flat stakes
retained as the baseline arm.
**Why:** The measured stake sweep is flat to ~$300 and peaks near $750, so the
liquidity bound dominates the theoretical optimum over most of the range.
**Confidence:** medium

### T16: Bankroll growth under an external cap
**Decision:** Model compounding as capped: once bankroll exceeds ~100x the
per-trade cap, returns become linear in qualifying days, not exponential.
Report terminal wealth under both unbounded and capped regimes.
**Confidence:** high

### T17: Scoring abstentions
**Decision:** Three-way ledger accounting: correct abstention (would have
lost) credited at the loss avoided; incorrect abstention (would have won)
debited at the profit foregone; and both reported separately from realised
PnL. Never treat an abstention as neutral.
**Why:** Neutral scoring makes the abstention rule look free, which
systematically biases the analysis toward trading more.
**Confidence:** high

## Stack & Libraries

No new dependencies. Python 3.12 stdlib only in core paths, matplotlib
confined to plotting helpers, per the project's standing rules. Every
mechanism here is arithmetic over data already fetched: shrinkage is a
one-dimensional minimisation, the decidability score is a weighted sum, and
the bootstrap already exists in `spx/strategy/analysis/bootstrap.py`.
**Build**, not adopt, for both mechanisms: nothing off the shelf implements
target-side decidability, and pulling in scikit-learn for a one-parameter fit
would violate the house rule for no benefit.

## Architecture

```
                 ┌──────────────┐
  futures arm ──►│              │
                 │  calibrate   │──► fused p(up), calibrated sigma
  replica arm ──►│  (shrinkage) │            │
        │        └──────────────┘            │
        │                                    ▼
        │   coverage, dispersion      ┌─────────────┐
        └──────────────────────────►  │ decidability│──► trade / abstain
                                      │   D vs k    │
                                      └─────────────┘
                                             │
   market price ─────────────────────────────┼──► edge ──► size (capped)
                                             │
                                             ▼
                                    per-day ledger row
```

The decidability score is deliberately **not** downstream of fusion: it
consumes microstructure observables directly, because routing it through the
posterior would reintroduce exactly the conflation it exists to break.

## Decisions Made For You (override in /refine)

1. **Chronological split over k-fold** (T1). Change this if you would rather
   maximise sample use than respect temporal order.
2. **Shrinkage over isotonic calibration** (T4). Change this if you would
   rather have a flexible calibrator and accept overfitting risk at low n.
3. **190 stratified days over the full calendar** (T9). Change this if you
   want to raise the spend cap and buy the whole period.
4. **Two fill assumptions rather than one** (T13). Change this if you would
   rather commit to a single conservative number.
5. **Near-tie days deferred behind WRDS** (T7). Change this if you want them
   attempted now with current weights, accepting that reconstruction error
   exceeds their signal.

## Key Findings

### F1: Selective prediction has a settled optimal form
**Finding:** Cost-based, bounded-improvement and bounded-coverage rejection
models all reduce to a Bayes classifier plus a randomized selection function
on a proper uncertainty score (R1).
**Implications:** Our abstention design reduces to choosing the right score.
That is the whole problem, and it licenses N1's framing.

### F2: Confidence thresholding is the acknowledged weak baseline
**Finding:** SelectiveNet's own motivation is that existing mechanisms are
"based mostly on a threshold over the prediction confidence of a pre-trained
network" (R2).
**Implications:** `CONF_COMMIT` is precisely that. It is a legitimate
incumbent to beat, and beating it is expected rather than remarkable.

### F3: The uncertainty split is not identifiable from the predictive alone
**Finding:** The epistemic/aleatoric decomposition cannot be recovered from
the posterior predictive distribution, even known exactly; structural
knowledge of the generating process is required (R3).
**Implications:** This is the strongest single justification for N1. No amount
of work on `σ_m` can yield decidability. It must come from outside the model,
and microstructure supplies it.

### F4: The reconstruction residual is not in the indicatives
**Finding:** Measured directly (2026-08-13, 29 cached days, n=14,340 name-days):
per-name |indicative/print - 1| has median 20.2 bp and p90 94.7 bp, and
Σw_i² = 0.02008 over normalised index weights. Independent per-name noise
therefore predicts an index error of 0.202% × √0.02008 = **2.9 bp**. Measured
index error is **12.9 bp**, 4.5x higher.
**The decisive comparison:** substituting *realised* cross prices for the
pre-open indicatives barely moves the error, 0.1372% versus 0.1287% MAE on
ordinary days (corr +0.918 versus +0.942). Perfect knowledge of every
constituent's opening price does not improve the index reconstruction.
**Implications:** The residual is systematic and lives in weights and
coverage, not in the auction data. No improvement to indicative quality,
timing, or the replica can reach it. This is why T7 routes to CRSP
point-in-time weights and why the near-tie stratum stays out of scope.

### F5: The photo moment carries no information
**Finding:** Swept 1.0s to 5.0s, quirk calls constant at 5/12 while live index
weight ranged 36.3% to 88.2%.
**Implications:** Not a tunable parameter. Excluded from the sweep, saving
degrees of freedom.

### F6: The replica and the strategy path are completely disconnected
**Finding:** Independent codebase mapping confirms no reference exists between
`spx/replica/` and `spx/strategy/` or `spx/backtest/` in either direction.
`spx.replica.pipeline` is invoked only from `spx/cli/auction.py`, prints to
stdout, and never persists into the dataset cache. Dataset rows carry
`date, off, es, nq, ym, rv_prev, vix1d_prev, release_morning` plus EWMA
fields, and nothing from the auction layer.
**Implications:** The paper's $321 result measures the pre-replica system
entirely. T14's insertion point is confirmed: the replica probability series
must be added to the day record built in `spx/strategy/data.py`, since that is
the only place the simulator reads signals from.

## References

### R1: Optimal strategies for reject option classifiers
**Source:** https://arxiv.org/abs/2101.12523 (Franc, Prusa, Voracek, 2021; retrieved 2026-08-13)
**Takeaway:** Three rejection formulations share one optimal strategy, a Bayes
classifier with a randomized Bayes selection function over a proper
uncertainty score. Provides the formal target our abstention rule should
approximate and the vocabulary for stating it.

### R2: SelectiveNet: A Deep Neural Network with an Integrated Reject Option
**Source:** https://arxiv.org/abs/1901.09192 (Geifman & El-Yaniv, 2019; retrieved 2026-08-13)
**Takeaway:** Joint optimisation of prediction and rejection beats thresholding
a pre-trained model's confidence, on risk-coverage across several datasets.
Establishes both the incumbent we beat and the metric to beat it on.

### R3: Decoupled PFNs: Identifiable Epistemic-Aleatoric Decomposition
**Source:** https://arxiv.org/abs/2605.06413 (Bergna, Depeweg, Hernández-Lobato, 2026; retrieved 2026-08-13)
**Takeaway:** The epistemic/aleatoric split is not identifiable from the
posterior predictive alone; the authors supply it through a controlled
generator. Licenses obtaining decidability from outside the model.

### R4: Learning low-frequency temporal patterns for quantitative trading
**Source:** https://arxiv.org/abs/2008.09481 (da Costa & Gebbie, 2020; retrieved 2026-08-13)
**Takeaway:** Applies CSCV and deflated/probabilistic Sharpe to judge whether
a trading result survives selection effects. The discipline is right; the
specific instruments need far more data than we have.

## Discarded Approaches

- **Top-N universe restriction.** Looked excellent in-sample (10/12, smooth
  plateau across N=20-50) and tied full-500 at 10/11 on the pre-registered
  holdout. Withdrawn on 2026-08-13. Not revisited without a new mechanism.
- **Sign/breadth aggregation to dodge weight error.** Tested five aggregators;
  all weight-robust variants were far worse on the clean ordinary-day set
  (10/17 and below versus 17/17). Magnitude is load-bearing because the index
  is cap-weighted and top-heavy.
- **Point-in-time weight reconstruction by price scaling.** Made results worse
  (ordinary MAE 0.129% to 0.149%). Killed the cheap proxy, not the hypothesis;
  true point-in-time weights still require CRSP.
- **Learned stacking for fusion.** No data to fit it at this n.

## Risks & Open Threads

- [ ] Ground truth rests on a single source while the stooq cross-check is
      vacuous. Must be repaired before any result is final.
- [ ] Polymarket history depth is assumed, not measured (T12).
- [ ] The decidability score is unvalidated until the minimal falsifying
      experiment runs. Everything downstream is gated on it.
- [ ] Near-tie stratum remains out of reach pending CRSP.
- [x] Photo moment: resolved, inert (F5).
- [x] Whether sign-based aggregation escapes the reconstruction wall:
      resolved, it does not.

## Artifact & Reproducibility

Released: the per-day ledger as JSON, the two scoring functions, the
pre-registration documents, and the day-selection rule. Rerun via
`tools/` scripts with pinned inputs; all randomness already uses fixed seeds
(Monte Carlo seed 7, bootstrap seed 20260719). Market data is licensed and
not redistributable, so the ledger ships with derived quantities and day
identifiers rather than raw vendor records. No personal data is involved.

## Threats to Validity

- **n is small.** 22 rule-derived days, 11 in the holdout. A 15-point accuracy
  separation is detectable; a 5-point one is not.
- **Single market, single venue, single year.** No claim generalises beyond
  the SPX daily open on Polymarket in 2025-2026.
- **Fills were never observed.** Every economic number rests on a modelled
  fill against an archived midpoint.
- **The day-selection rule was derived in-period**, so the disagreement
  stratum is not a clean out-of-sample population (T8).
- **Ground truth is single-sourced** while the cross-check is broken.
- **Survivorship in weights.** Current index membership applied to historical
  dates, up to 11 months of drift.

## Publication Assessment

**Refuting our own claims first.**

*N1 (decidability).* The strongest case against: `D` is a monotone function of
`|ĝ|` divided by a quantity that barely varies day to day, so it may be
nothing more than "abstain when the prediction is small" wearing formal dress.
That naive rule is in the baseline set precisely to catch this, and if `D`
does not beat it, N1 is not a contribution. This is the single most likely way
the work fails.

*N2 (shrinkage).* The strongest case against: fixing z-RMS is trivial and
well known; calling a scalar multiplication a contribution is generous. The
honest framing is that the *diagnosis* (sign reliable, magnitude inflated,
3x) is the finding, and the fix is the obvious consequence. Tier 1-B, not
Tier 1, for that reason.

*H3 (economics).* The strongest case against: the entire economic layer rests
on midpoint fills in a market doing $30-48k/day. If real fills are materially
worse, the edge may not survive contact with the book, and no amount of
modelling settles that. Only live paper-trading would.

**Calibration.** This is a well-built system with one genuinely interesting
idea. The interesting idea is not the predictor; it is the observation that a
forecasting target can be *undefined at the required resolution*, that this is
distinct from model uncertainty, that it is not recoverable from the model's
own posterior (R3), and that microstructure supplies the missing handle. That
observation generalises beyond this project.

The trading result, if it holds, is a modest edge in a thin market and is not
by itself publishable. The methodological finding plus the four silent-
corruption defects documented on 2026-08-13 make a credible short paper on
*how* microstructure-based index reconstruction goes wrong, which is more
useful to others than the returns.

**Ranked paths to a genuine contribution:** (1) the decidability result, if
H1 survives, available now; (2) the reconstruction-fidelity study showing
where index replication error actually lives, available now and needing no
new data; (3) the economic result, which requires live validation and is the
weakest of the three.

## Build Plan

**Phase 1 (instrument + the safety rails that make measurement honest, no new
data).** Three things, together, because they are the same concern:
(a) hard `as_of` enforcement threaded through `snapshots()` so no post-cutoff
data can enter any prediction, which is what the 2026-08-13 lookahead defect
required and which is equally a production requirement (T10);
(b) liveness assertions on the three known silent-failure dependencies -- index
weights, the stooq cross-check, per-slice entitlement -- each failing loudly
(T11);
(c) the per-day ledger and the decidability score, then the minimal falsifying
experiment.
Gate: if `D` fails to separate top and bottom halves by 15 points, stop and
write the negative result.

Rationale for folding the live-path rails into phase 1 rather than phase 6:
C6 forbids backtest-first-then-productionise, and these particular rails are
not hardening. An unenforced cutoff produced a partial oracle that scored a
result we had to retract, and a silently dead dependency produced a
vacuously-passing ground-truth audit. They are correctness requirements for
the measurement itself, so they cannot be deferred without the measurement
being untrustworthy again.

**Phase 2 (calibration).** Fit `λ` on tuning days. Verify unit z-RMS and sign
retention. Baseline arms: raw, Platt, isotonic.

**Phase 3 (data).** Buy ~190 stratified days (T9). Re-fetch Polymarket history
and measure its true depth (T12). Repair the stooq cross-check (T11).

**Phase 4 (integration).** Replica arm into `data.py` and the simulator.
Sizing on calibrated confidence, capped by liquidity. Full ledger over the
market-history window under both fill assumptions.

**Phase 5 (analysis).** Per-decision forensics under C9 discipline:
mechanisms only, degrees of freedom counted, every proposed change tested on
days that did not produce it.

**Phase 6 (live orchestration).** The morning loop itself: checkpoint
scheduling, crash recovery, fail-closed abstention when any input is stale.
The correctness rails it depends on already landed in phase 1. Replay-provable
per the prior vision's C4; the real-morning shakedown needs a trading day and
is expected to be marked BLOCKED within any single run.

## Degrees-of-Freedom Ledger (C10)

Outcome-informed choices are counted here and the count is reported with every
result. Budget: at n≈22 rule-derived days, 4-5 exhausts the statistical
content.

| # | Parameter | Fitted on | Outcome-dependent? | Status |
|---|---|---|---|---|
| 1 | `λ` shrinkage | tuning days, z-RMS only | No -- targets unit variance, never PnL | spent |
| 2 | `k` decidability threshold | tuning days, risk-coverage | Partially -- coverage is chosen, error is measured | spent |
| 3 | Kelly fraction (T15) | tuning days | Yes -- must be declared before the evaluation set is touched | reserved |
| — | Fusion weights (T5) | not fitted; inverse-variance formula | No | free |
| — | Photo moment | not fitted; measured inert (F5) | No | free |
| — | `PREVIEW_SIGMA` | measured directly from dispersion | No | free |

T3 and T5 are reconciled here: fusion weights are **formula-derived, not
fitted**, so they cost nothing from the budget. T15's Kelly fraction is a real
free parameter and is counted, which the first draft of this doc omitted.

**Paper handoff.** `Formal Model` -> Method; `Related Work Map` -> Related
Work; `Evaluation Plan` -> Experiments; `Novel Contributions` ->
Contributions; `Threats to Validity` -> Limitations; `Artifact &
Reproducibility` -> reproducibility checklist. Run `/paper` after Phase 5.
