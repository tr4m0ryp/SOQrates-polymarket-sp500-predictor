# Architecture and Data Flow

## Execution model

Every command runs as `python3 . <command>` from the repo root. Python executes
`__main__.py`, which is three lines: import `main` from `open_predictor.cli` and call it.
Because the script directory (the repo root) lands on `sys.path`, `import open_predictor`
resolves without any install step. `open_predictor/` is the single code package; there is
no setup.py, no entry points, no third-party dependency in the core paths.

`open_predictor/cli/__init__.py` builds the argparse subcommand table and dispatches to
command bodies in `open_predictor/cli/market.py`, `open_predictor/cli/sources.py`,
`open_predictor/cli/auction.py`, `open_predictor/cli/newscmd.py`, and `open_predictor/cli/strategy.py`. All
heavy imports happen inside the command functions, so parsing `--help` touches
nothing else.

`open_predictor/config.py` holds the shared constants: the `America/New_York` zoneinfo
(`NY`), the `.cache/` directory (created on import, gitignored), fitted model
constants (`K_DEFAULT = 0.767` attenuation, `EWMA_LAMBDA = 0.94`,
`CONF_COMMIT = 0.65`), and the `QUIRK_DAYS` list of days where ES futures held
one direction but the official open printed the opposite.

The top-level package `__init__.py` files (`open_predictor/sources/market`, `open_predictor/forecast/model`, `open_predictor/trading/polymarket`,
`open_predictor/forecast/backtest`, `open_predictor/forecast/news`, `open_predictor/forecast/auction`, `open_predictor/trading/strategy`) are empty; intent
lives in module docstrings and the subpackage `__init__.py` files.

## Flow 1: daily prediction (`predict`, `backtest`)

`open_predictor/forecast/backtest/dataset.py` builds `.cache/dataset.json`: hourly overnight gap
paths for ES/NQ/YM from `open_predictor/sources/market/futures.py` (which wraps the Yahoo v8 chart
API in `open_predictor/sources/market/yahoo.py`), a release-morning flag from
`open_predictor/sources/macro/releases.py` (FRED release-dates API, first-Friday NFP fallback),
and EWMA regime annotation from `open_predictor/forecast/model/regime.py`.

`cmd_predict` in `open_predictor/cli/market.py` loads the dataset, fits `ModelV13` from
`open_predictor/forecast/model/core.py`, reads the live ES and NQ gaps for the current ET hour,
and calls `model.predict(row, hour)` for (mu, sigma, P(up)). It then fetches
today's Polymarket "SPX Opens Up or Down" market via `open_predictor/trading/polymarket/gamma.py` and
scores the divergence with `open_predictor/trading/polymarket/edge.py` (`EDGE_THRESHOLD = 0.05`, no-bet
below `CONF_COMMIT`).

Model cores in `open_predictor/forecast/model/core.py`: `Baseline`, `ModelV12` (ES only),
`ModelV13` (adds VIX1D sigma and the NQ-ES spread), and `ModelProd`, which
uses v1.3 for hours 0-4 and v1.2 for hours 5-9. `open_predictor/forecast/model/fusion.py` is the
inverse-variance combiner every other flow feeds into.

```
Yahoo chart API              FRED release dates
      |                             |
open_predictor/sources/market/futures.py         open_predictor/sources/macro/releases.py
      \                            /
       open_predictor/forecast/backtest/dataset.py  ->  .cache/dataset.json
                    |
      open_predictor/forecast/model/core.py (ModelV13.fit / .predict)
      open_predictor/forecast/model/regime.py (EWMA + RV sigma scaling)
                    |
             (mu, sigma) -> P(up)
                    |            open_predictor/trading/polymarket/gamma.py (market P(up))
                    +------------------+
                    |
            open_predictor/trading/polymarket/edge.py -> action + edge
```

`backtest` runs the same dataset through `open_predictor/forecast/backtest/run.py`: chronological
train/test halves, metrics at hours 0/4/7/9, and a quirk-day report.

## Flow 2: stage-3 auction replica (`databento-pull` / `lseg-pull`, `stage3`)

Vendors first: `open_predictor/forecast/auction/vendors/databento/source.py` (primary,
`databento-pull --date D`) caches a day of Nasdaq NOII, NYSE imbalance, cross
prints, and pre-open NBBO as raw JSON; `open_predictor/forecast/auction/vendors/lseg/` (fallback,
`lseg-pull`) writes a Tick History CSV under `.cache/lseg/`. Also under
`open_predictor/forecast/auction/vendors/`: `itch/` and `taq/` parse raw exchange files for
research, and `stitch/` holds free live fallbacks (Webull NOII, Massive
imbalance).

`cmd_stage3` in `open_predictor/cli/auction.py` picks the source (databento if
`DATABENTO_API_KEY` is set), extracts each ticker's last indicative price
before the open, fetches prior closes from Yahoo, and hands both dicts to
`open_predictor/forecast/auction/pipeline.py`:

- `replica_estimate` calls `open_predictor/forecast/auction/core/assembly.py` (`first_tick_gap`,
  `replica_sigma`) over constituents built from `open_predictor/sources/market/weights.py`
  (Slickcharts weights, nasdaqlisted.txt decides Nasdaq vs NYSE listing).
  Nasdaq names enter at their indicative price; NYSE names stay at prior
  close by default because measured NYSE indicative noise is ~29bp vs 0-5bp
  for Nasdaq NOII.
- `replica_distribution` runs the Monte Carlo in
  `open_predictor/forecast/auction/core/montecarlo.py` with per-stock print probabilities from
  `open_predictor/forecast/auction/core/timing.py` (venue priors until fitted on print
  timestamps). Output: mean, sigma, P(up), quantiles, and pivotal names.
- `fused_p_up` blends the replica (mu, sigma) with the futures view through
  `open_predictor/forecast/model/fusion.py`.

The command ends by comparing the replica against the official ^GSPC gap for
that date (MATCH/MISS).

## Flow 3: news layer (`news-*` commands)

Sources in `open_predictor/forecast/news/sources/`: `gdelt.py` (keyless archive, 15-min index,
rate limit >= 5s per call) and `alpaca.py` (real-time headline wire). Work
splits into Group A (slow context, prefetched once at ~00:05 ET by
`open_predictor/forecast/news/ops/prefetch.py`) and Group B (continuous feeds, cadence and
checkpoints in `open_predictor/forecast/news/ops/schedule.py`).

The LLM stack in `open_predictor/forecast/news/llm/`: `runner.py` is a provider-agnostic
chat-completions client (env `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL`,
optional fallback chain), `prompt.py` defines the strict Group-A output
contract (sigma multiplier `m_A` in [1.0, 2.5], direction capped at |0.3|),
and `groupb.py` turns a classified shock into a fitted voice
(mu_B, sigma_B, sigma multiplier). The news voice enters
`open_predictor/forecast/model/fusion.py combine` as one more (mu, sigma) estimate with
sigma_A >= 0.25%, so it can nudge and widen but never dominate the futures
model. `open_predictor/forecast/news/eval/` scores the layer historically: mistake inventory,
decisive-hour timing profile, headline replay, and provider bench.

Note: the live `predict` command does not call the news layer yet; the fusion
of the news voice runs in eval replay and in the strategy dataset overlay.

## Flow 4: strategy sim (`pm-history`, `strategy-data`, `strategy-run`, `strategy-search`)

`open_predictor/trading/polymarket/history.py` enumerates every historical daily SPX-open market
(gamma series id 10945) and caches minute price curves under
`.cache/pm_history/`. `open_predictor/trading/strategy/data.py` joins each day's curve (CLOB
midpoints, not trades) with the model's hourly P(up), including a
deterministic Group-B overlay (no LLM call), into `.cache/strategy_days.json`.

`open_predictor/trading/strategy/engine/sim.py` runs a rule family over the day records with
execution realism from `open_predictor/trading/strategy/engine/execution.py` (taker fee since
2026-03-30, spread, book impact; makers pay zero) and stake selection from
`open_predictor/trading/strategy/engine/sizing.py`. Families are registered in
`open_predictor/trading/strategy/rules/base.py` (`STRATEGIES`: hold, flow_flip, takeprofit,
longshot, scale_in, plus composite and crowd-fade modules).
`strategy-search` grid-scans parameters on the train half.
`open_predictor/trading/strategy/analysis/` adds bootstrap confidence bands and plots.

## Where to look

- `open_predictor/cli/__init__.py`: the full command table, one place to see every flow's entry point.
- `open_predictor/config.py`: shared constants, cache location, quirk-day list.
- `open_predictor/cli/market.py`: `cmd_predict`, the daily prediction flow end to end.
- `open_predictor/forecast/auction/pipeline.py`: stage-3 assembly and fusion, with the Nasdaq-vs-NYSE trust rationale in its docstring.
- `open_predictor/forecast/model/fusion.py`: the inverse-variance combiner all flows converge on.
- `open_predictor/trading/strategy/data.py`: how market curves and model output join for the simulator.
