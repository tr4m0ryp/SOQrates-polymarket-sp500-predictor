# Backtesting and Evaluation

Everything evaluation-related lives in `open_predictor/forecast/backtest/`: five files, no
subpackages. `dataset.py` builds and caches the daily dataset, `run.py` is the
metric runner behind `python3 . backtest`, `baselines.py` prints the
crowd/k=1/logistic comparison table, `reality_check.py` corrects the strategy
search for selection bias, and `plot.py` draws the reliability diagram.
Only `run.py` is wired into the CLI (`open_predictor/cli/market.py` ->
`open_predictor/cli/__init__.py`); the other three run as modules from the repo root.

## Dataset builder (`open_predictor/forecast/backtest/dataset.py`)

`build()` joins Yahoo ^GSPC daily open/close with hourly ES/NQ/YM futures gap
paths from `open_predictor/sources/market/futures.py`. One row per trading day with: `date`, `off`
(official open gap in percent of prior close), `es`/`nq`/`ym` (hour -> gap
maps, hour 0..9 ET), `rv_prev` (prior-day realized variance), `vix1d_prev`
(prior ^VIX1D close), and `release_morning` (from `open_predictor/sources/macro/releases.py`).
Days whose ES path is missing, shorter than 9 hours, or lacks hour 0 are
dropped. `annotate_ewma` (`open_predictor/forecast/model/regime.py`) stamps the volatility EWMA,
then the last `DATASET_DAYS = 480` rows are kept (`LOOKBACK_DAYS = 720` is the
Yahoo 60-minute-history fetch window; both in `open_predictor/config.py`).

`load(rebuild=False)` reads `.cache/dataset.json` when present, else builds
and writes it. `python3 . backtest --rebuild` forces a rebuild; deleting
`.cache/` does the same (the whole directory is gitignored). JSON turns the
hour keys into strings, so `load` runs `_intify` to restore int keys.
`split(rows)` cuts the list in half chronologically: first half train, second
half test. There is no shuffling anywhere.

## Metric runner (`open_predictor/forecast/backtest/run.py`)

`python3 . backtest` fits `Baseline`, `ModelV12`, and `ModelV13` (all from
`open_predictor/forecast/model/core.py`) on the train half and scores each on the test half at
`EVAL_HOURS = (0, 4, 7, 9)` ET. Per model and hour, `metrics()` reports:

- `brier` and `acc`: Brier score and direction accuracy, with `p > 0.5`
  calling UP.
- `coinflip`: fraction of days where confidence `max(p, 1-p)` is below
  `CONF_COMMIT = 0.65`, the no-bet threshold from `open_predictor/config.py`.
- `comm_acc`: accuracy on the committed (confidence >= 0.65) days only.
- `oc80`: count of days that were confident at >= 0.80 and still wrong.

After the table, `quirk_report()` prints the quirk-day block: `QUIRK_DAYS` in
`open_predictor/config.py` lists 12 dates (2025-09-12 through 2026-07-10) where ES held a
direction overnight but the official print came out opposite or tiny. Each is
evaluated at 9:00 under v1.3 and labelled `safe` (low confidence, or right) or
`CONF-WRONG`. The runner's closing note is the design position: quirk
direction cannot be recovered from futures data and needs the stage-3 auction
replica (`open_predictor/forecast/auction/`).

## Baselines table (`open_predictor/forecast/backtest/baselines.py`)

Compares four methods on the paper's validated window: the 200 dataset days
ending 2026-07-13, split in half, test = the 100 days 2026-02-12..2026-07-13.
Decision times are 00:00, 04:00, and 09:00 ET, plus a crowd-only 09:29 row.

- `crowd`: Polymarket UP-token midpoint at the decision minute, read from the
  cached minute curves under `.cache/pm_history/` (populated by
  `python3 . pm-history`; no fetching at table time).
- `k=1`: sign of the overnight ES gap at the decision hour, probability hard
  0/1, so Brier equals the miss rate.
- `logistic`: sigmoid(b0 + b1 * gap) on the ES gap alone, one Newton-Raphson
  fit per hour on the train half only (stdlib, tiny ridge).
- `soqrates`: `ModelProd` from `open_predictor/forecast/model/core.py`, the production hand-off
  (v1.3 for hours < 5, v1.2 from 5:00 on), fitted on the train half.

A paired block re-scores the model on exactly the crowd-covered subset so
crowd-vs-model cells compare the same days. The module docstring says
`python3 -m backtest.baselines`, which is stale: there is no top-level
`backtest` package. The working invocation from the repo root is
`python3 -m open_predictor.forecast.backtest.baselines`. Same applies to `reality_check.py`.

## Reality check (`open_predictor/forecast/backtest/reality_check.py`)

The strategy lab picked the best of 15 verified candidates (hold, flow_flip,
convergence, takeprofit, longshot parameterizations, hard-coded in
`CANDIDATES`), and quoting the winner's raw test PnL overstates significance.
This script applies White's reality check (White 2000): the statistic is the
max over the family of sqrt(n) * mean daily flat-stake PnL on the strategy
test half (built by `open_predictor/trading/strategy/data.py`, simulated via
`open_predictor/trading/strategy/engine/sim.py`), and the null comes from a stationary bootstrap
(Politis-Romano 1994; mean block 5 days, 10,000 draws, seed 20260719)
resampled jointly across candidates to preserve correlation. All candidates
run at flat $100 stakes; days the volume gate skips count as $0. It prints
both the naive single-hypothesis bootstrap p and the family-adjusted p, for
the recorded 15 and for an extended family that adds the two later survivors
(`first_signal`, `full_strategy`), since selection continued past the
recorded workflow.

## Reliability diagram (`open_predictor/forecast/backtest/plot.py`)

`reliability_diagram()` fits `ModelProd` on the first 100 days of the fixed
window 2025-09-09..2026-07-13 and evaluates the held-out 100 at 9:00 ET, the
latest hour in the hourly dataset. Predictions are binned into deciles of
P(up); each point shows the observed UP frequency with a 95% Wilson interval,
and a lower panel shows the day count per bin. Output goes to
`docs/research/plots/reliability_diagram.png` and `.pdf`. matplotlib is imported
only inside this module, per the project rule.

## Evaluation conventions (from `CLAUDE.md`)

- Train/test = chronological halves of the dataset window; nothing is ever
  fitted on the test half. `dataset.split`, `baselines.py`, `plot.py`, and
  `open_predictor/trading/strategy/data.split` all follow this.
- Quirk days are tracked as a named list (`QUIRK_DAYS` in `open_predictor/config.py`) and
  reported separately; the honest metric there is safety (abstain or be
  right), not accuracy.
- Ground truth is the Yahoo ^GSPC daily open, cross-checked against stooq by
  `python3 . ground-truth` (`open_predictor/sources/market/ground_truth.py`, tolerance 0.75 index
  points). Disagreement days are to be excluded from fits. Note: the dataset
  builder has no automatic filter for them; the audit lists them and exclusion
  is a manual step. As implemented, the audit has reported full agreement.
- All timestamps are ET; gaps are percent of prior close; caches live under
  `.cache/` and are safe to delete.

## Where to look

- `open_predictor/forecast/backtest/dataset.py`: dataset build, cache, chronological split.
- `open_predictor/forecast/backtest/run.py`: the `python3 . backtest` metrics and quirk table.
- `open_predictor/forecast/backtest/baselines.py`: crowd / k=1 / logistic / ModelProd table.
- `open_predictor/forecast/backtest/reality_check.py`: White's reality check on the strategy family.
- `open_predictor/forecast/backtest/plot.py`: reliability diagram for the production model.
- `open_predictor/config.py`: `CONF_COMMIT`, `DATASET_DAYS`, `QUIRK_DAYS`.
