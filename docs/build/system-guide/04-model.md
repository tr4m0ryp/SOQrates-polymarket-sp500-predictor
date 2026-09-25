# The Prediction Model

The model answers one question per day: what is the probability that the
official S&P 500 opening print (^GSPC daily open) lands above the prior close?
Everything in `open_predictor/forecast/model/` maps an overnight ES futures gap to a Gaussian
estimate of the official gap, `(mu, sigma)`, and converts it to
`P(up) = Phi(mu / sigma)` (`phi` in `open_predictor/forecast/model/core.py`). The package has three
modules: `open_predictor/forecast/model/regime.py` (volatility regime scaler), `open_predictor/forecast/model/core.py`
(the model cores), and `open_predictor/forecast/model/fusion.py` (inverse-variance pooling).
`open_predictor/forecast/model/__init__.py` is empty; import from the submodules directly.

## Input rows and the hour convention

Each dataset row (built in `open_predictor/forecast/backtest/dataset.py`) covers one trading day:
`off` is the official open gap in percent of prior close, and `es`, `nq`, `ym`
are hourly futures gap paths from `open_predictor/sources/market/futures.py`. The hour key `h` in
0..9 is the ET clock hour on the prediction day, so `es[9]` is the ES gap at
9:00 ET, 30 minutes before the open. All gaps are measured against the
prior-day 16:00 ET futures price, in percent. Rows also carry `rv_prev`
(prior-day realized variance, sum of squared hourly ES returns 10:00-16:00),
`vix1d_prev` (prior-day ^VIX1D close), and `release_morning` (macro release at
8:30, from `open_predictor/sources/macro/`).

## Regime scaler (`open_predictor/forecast/model/regime.py`)

`annotate_ewma` attaches `ewma_prev` to each row: an EWMA of the squared 9:00
ES gap with decay `EWMA_LAMBDA = 0.94`. The value stored on a row is the EWMA
of prior days only; the current day's gap updates the accumulator after the
row is stamped, so there is no lookahead. The first row has no prior EWMA and
is dropped.

`RegimeScaler.fit` computes train-set means of `ewma_prev`, `rv_prev`, and
(when `use_vix=True`) `vix1d_prev`. `mult(row)` normalizes each signal by its
train mean and blends: `0.5*ewma + 0.5*rv` without VIX, or
`0.4*ewma + 0.3*rv + 0.3*vix^2` with it, then returns
`sqrt(max(blend, 0.05))`. The result is a per-day sigma multiplier: about 1.0
in a normal regime, larger after volatile nights. `terciles` splits the train
days into three regime buckets by this multiplier; `tercile_of` assigns a new
day to a bucket.

## Model cores (`open_predictor/forecast/model/core.py`)

All cores share the linear form `mu = A0 + k * es[h]` and differ in how `k`
and `sigma` adapt. `ols_slope` fits `k` by ordinary least squares and falls
back to `K_DEFAULT` with fewer than 8 pairs.

**Baseline** (`name="baseline"`): frozen `k = K_DEFAULT` for every day and
hour, one static sigma per hour from train residuals. The reference arm in the
backtest table.

**ModelV12** (`name="v1.2"`, ES only): three refinements over Baseline.
First, `k` is fitted per regime tercile (calm days attenuate differently from
wild ones). Second, for early hours 0-4 (`SMALL_GAP_HOURS`) with
`|es[h]| < SMALL_GAP` (0.25%), a separate small-gap `k` per hour replaces the
tercile slope, because tiny overnight gaps behave differently. Third, sigma is
per-hour residual scale times the regime multiplier, and on release mornings
before 8:30 (`h < 8.5` in `predict`) sigma is widened by a fitted multiplier
`m_release`: the residual-variance ratio of release vs normal mornings at
hours 0, 4, 7, clamped to `RELEASE_MULT_BOUNDS = (1.0, 2.5)`, defaulting to
`NFP_SIGMA_MULT = 1.3` when fewer than 8 release samples exist.

**ModelV13** (`name="v1.3"`): ModelV12 with two flags flipped.
`use_vix=True` adds VIX1D to the regime blend, and `use_nq=True` adds a
per-hour NQ-ES spread term: `mu += c_nq[h] * (nq[h] - es[h])`, with `c_nq`
fitted by OLS on the residual after the ES term (default 0.0).

**ModelProd** (`name="prod"`): the production switch. It fits both a
ModelV13 and a ModelV12 and routes by hour: v1.3 for `h < 5` (early, where
VIX1D and the NQ spread sharpen the call), v1.2 for `h >= 5` (late, where the
plain ES view is better calibrated). This is what `open_predictor/trading/strategy/data.py`,
`open_predictor/cli/newscmd.py`, and `open_predictor/forecast/backtest/plot.py` use.

## Inverse-variance fusion (`open_predictor/forecast/model/fusion.py`)

`combine` pools any list of `(mu, sigma)` estimates by weighting each with
`1/sigma^2` (Kalman-style), returning the pooled mean and
`sqrt(1/sum(weights))`. Estimates with `sigma <= 0` are skipped. `prob_up`
converts the pooled pair to `P(up)`. The only current caller is
`open_predictor/forecast/auction/pipeline.py` (`fused_p_up`), which blends the stage-3 auction
replica's gap estimate with the futures-model view; the design allows more
stages to be added as extra `(mu, sigma)` entries.

## Constants in `open_predictor/config.py`

| Constant | Value | Meaning |
|---|---|---|
| `A0` | 0.0092 | Intercept of the official-gap regression, in % |
| `K_DEFAULT` | 0.767 | Pooled futures-to-official attenuation slope; OLS fallback |
| `EWMA_LAMBDA` | 0.94 | Decay for the squared-gap EWMA in the regime scaler |
| `SMALL_GAP` | 0.25 | Absolute gap (%) below which the small-gap `k` applies |
| `SMALL_GAP_HOURS` | (0,1,2,3,4) | Hours eligible for the small-gap `k` |
| `NFP_SIGMA_MULT` | 1.3 | Fallback release-morning sigma widening |
| `RELEASE_MULT_BOUNDS` | (1.0, 2.5) | Clamp on the fitted release multiplier |
| `CONF_COMMIT` | 0.65 | Below this `max(p, 1-p)`, the call is a coin flip: no bet |
| `LOOKBACK_DAYS` | 720 | Hourly futures history window (Yahoo 60m cap ~730d) |
| `DATASET_DAYS` | 480 | Trading days kept in the backtest dataset |
| `QUIRK_DAYS` | 12 dates | Days where ES held a direction but the official open printed opposite or near zero |

`config.py` also defines `NY` (the `America/New_York` zoneinfo, all timestamps
are ET) and `CACHE` (the gitignored `.cache/` directory, created on import).

`CONF_COMMIT` drives behavior in two places: `open_predictor/trading/polymarket/edge.py` refuses to bet
below it (and additionally requires a 0.05 model-vs-market price edge), and
`open_predictor/forecast/backtest/run.py` reports the coin-flip fraction and committed-call
accuracy separately. `QUIRK_DAYS` feeds `quirk_report` in
`open_predictor/forecast/backtest/run.py`: at 9:00 the model is judged "safe" on a quirk day if it
either stood down (confidence below `CONF_COMMIT`) or called the direction
right. The runner's own note states the quirk direction is unfixable from
futures data alone and needs the stage-3 auction replica.

## Train/test discipline

`split` in `open_predictor/forecast/backtest/dataset.py` cuts the chronological row list in half:
first half train, second half test. Nothing is ever fitted on the test half.
All fitting respects this: `RegimeScaler` means, tercile bounds, every OLS
slope, per-hour sigmas, and the release multiplier come from `fit(train)`
only. `annotate_ewma` is additionally lookahead-free within a row. The
backtest (`open_predictor/forecast/backtest/run.py`) evaluates Baseline, v1.2, and v1.3 on the
test half at hours 0, 4, 7, 9 with Brier score, accuracy, coin-flip fraction,
committed accuracy, and an `oc80` count (calls at 80%+ confidence that were
wrong).

## Where to look

- `open_predictor/forecast/model/core.py`: all four model cores and the shared `phi`/`ols_slope` helpers
- `open_predictor/forecast/model/regime.py`: EWMA annotation, `RegimeScaler`, terciles
- `open_predictor/forecast/model/fusion.py`: inverse-variance pooling used by stage 3
- `open_predictor/config.py`: every named constant, with inline comments
- `open_predictor/forecast/backtest/dataset.py`: row schema, cache, and the chronological split
- `open_predictor/forecast/backtest/run.py`: metrics table and the quirk-day report
