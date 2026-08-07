# Architecture and Data Flow

## Execution model

Every command runs as `python3 . <command>` from the repo root. Python executes
`__main__.py`, which is three lines: import `main` from `spx.cli` and call it.
Because the script directory (the repo root) lands on `sys.path`, `import spx`
resolves without any install step. `spx/` is the single code package; there is
no setup.py, no entry points, no third-party dependency in the core paths.

`spx/cli/__init__.py` builds the argparse subcommand table and dispatches to
command bodies in `spx/cli/market.py`, `spx/cli/sources.py`,
`spx/cli/auction.py`, `spx/cli/newscmd.py`, and `spx/cli/strategy.py`. All
heavy imports happen inside the command functions, so parsing `--help` touches
nothing else.

`spx/config.py` holds the shared constants: the `America/New_York` zoneinfo
(`NY`), the `.cache/` directory (created on import, gitignored), fitted model
constants (`K_DEFAULT = 0.767` attenuation, `EWMA_LAMBDA = 0.94`,
`CONF_COMMIT = 0.65`), and the `QUIRK_DAYS` list of days where ES futures held
one direction but the official open printed the opposite.

The top-level package `__init__.py` files (`spx/data`, `spx/model`, `spx/pm`,
`spx/backtest`, `spx/news`, `spx/replica`, `spx/strategy`) are empty; intent
lives in module docstrings and the subpackage `__init__.py` files.

## Flow 1: daily prediction (`predict`, `backtest`)

`spx/backtest/dataset.py` builds `.cache/dataset.json`: hourly overnight gap
paths for ES/NQ/YM from `spx/data/futures.py` (which wraps the Yahoo v8 chart
API in `spx/data/yahoo.py`), a release-morning flag from
`spx/macro/releases.py` (FRED release-dates API, first-Friday NFP fallback),
and EWMA regime annotation from `spx/model/regime.py`.

`cmd_predict` in `spx/cli/market.py` loads the dataset, fits `ModelV13` from
`spx/model/core.py`, reads the live ES and NQ gaps for the current ET hour,
and calls `model.predict(row, hour)` for (mu, sigma, P(up)). It then fetches
today's Polymarket "SPX Opens Up or Down" market via `spx/pm/gamma.py` and
scores the divergence with `spx/pm/edge.py` (`EDGE_THRESHOLD = 0.05`, no-bet
below `CONF_COMMIT`).

Model cores in `spx/model/core.py`: `Baseline`, `ModelV12` (ES only),
`ModelV13` (adds VIX1D sigma and the NQ-ES spread), and `ModelProd`, which
uses v1.3 for hours 0-4 and v1.2 for hours 5-9. `spx/model/fusion.py` is the
inverse-variance combiner every other flow feeds into.

```
Yahoo chart API              FRED release dates
      |                             |
spx/data/futures.py         spx/macro/releases.py
      \                            /
       spx/backtest/dataset.py  ->  .cache/dataset.json
                    |
      spx/model/core.py (ModelV13.fit / .predict)
      spx/model/regime.py (EWMA + RV sigma scaling)
                    |
             (mu, sigma) -> P(up)
                    |            spx/pm/gamma.py (market P(up))
                    +------------------+
                    |
            spx/pm/edge.py -> action + edge
```

`backtest` runs the same dataset through `spx/backtest/run.py`: chronological
train/test halves, metrics at hours 0/4/7/9, and a quirk-day report.

## Flow 2: stage-3 auction replica (`databento-pull` / `lseg-pull`, `stage3`)

Vendors first: `spx/replica/vendors/databento/source.py` (primary,
`databento-pull --date D`) caches a day of Nasdaq NOII, NYSE imbalance, cross
prints, and pre-open NBBO as raw JSON; `spx/replica/vendors/lseg/` (fallback,
`lseg-pull`) writes a Tick History CSV under `.cache/lseg/`. Also under
`spx/replica/vendors/`: `itch/` and `taq/` parse raw exchange files for
research, and `stitch/` holds free live fallbacks (Webull NOII, Massive
imbalance).

`cmd_stage3` in `spx/cli/auction.py` picks the source (databento if
`DATABENTO_API_KEY` is set), extracts each ticker's last indicative price
before the open, fetches prior closes from Yahoo, and hands both dicts to
`spx/replica/pipeline.py`:

- `replica_estimate` calls `spx/replica/core/assembly.py` (`first_tick_gap`,
  `replica_sigma`) over constituents built from `spx/data/weights.py`
  (Slickcharts weights, nasdaqlisted.txt decides Nasdaq vs NYSE listing).
  Nasdaq names enter at their indicative price; NYSE names stay at prior
  close by default because measured NYSE indicative noise is ~29bp vs 0-5bp
  for Nasdaq NOII.
- `replica_distribution` runs the Monte Carlo in
  `spx/replica/core/montecarlo.py` with per-stock print probabilities from
  `spx/replica/core/timing.py` (venue priors until fitted on print
  timestamps). Output: mean, sigma, P(up), quantiles, and pivotal names.
- `fused_p_up` blends the replica (mu, sigma) with the futures view through
  `spx/model/fusion.py`.

The command ends by comparing the replica against the official ^GSPC gap for
that date (MATCH/MISS).

## Flow 3: news layer (`news-*` commands)

Sources in `spx/news/sources/`: `gdelt.py` (keyless archive, 15-min index,
rate limit >= 5s per call) and `alpaca.py` (real-time headline wire). Work
splits into Group A (slow context, prefetched once at ~00:05 ET by
`spx/news/ops/prefetch.py`) and Group B (continuous feeds, cadence and
checkpoints in `spx/news/ops/schedule.py`).

The LLM stack in `spx/news/llm/`: `runner.py` is a provider-agnostic
chat-completions client (env `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL`,
optional fallback chain), `prompt.py` defines the strict Group-A output
contract (sigma multiplier `m_A` in [1.0, 2.5], direction capped at |0.3|),
and `groupb.py` turns a classified shock into a fitted voice
(mu_B, sigma_B, sigma multiplier). The news voice enters
`spx/model/fusion.py combine` as one more (mu, sigma) estimate with
sigma_A >= 0.25%, so it can nudge and widen but never dominate the futures
model. `spx/news/eval/` scores the layer historically: mistake inventory,
decisive-hour timing profile, headline replay, and provider bench.

Note: the live `predict` command does not call the news layer yet; the fusion
of the news voice runs in eval replay and in the strategy dataset overlay.

## Flow 4: strategy sim (`pm-history`, `strategy-data`, `strategy-run`, `strategy-search`)

`spx/pm/history.py` enumerates every historical daily SPX-open market
(gamma series id 10945) and caches minute price curves under
`.cache/pm_history/`. `spx/strategy/data.py` joins each day's curve (CLOB
midpoints, not trades) with the model's hourly P(up), including a
deterministic Group-B overlay (no LLM call), into `.cache/strategy_days.json`.

`spx/strategy/engine/sim.py` runs a rule family over the day records with
execution realism from `spx/strategy/engine/execution.py` (taker fee since
2026-03-30, spread, book impact; makers pay zero) and stake selection from
`spx/strategy/engine/sizing.py`. Families are registered in
`spx/strategy/rules/base.py` (`STRATEGIES`: hold, flow_flip, takeprofit,
longshot, scale_in, plus composite and crowd-fade modules).
`strategy-search` grid-scans parameters on the train half.
`spx/strategy/analysis/` adds bootstrap confidence bands and plots.

## Where to look

- `spx/cli/__init__.py`: the full command table, one place to see every flow's entry point.
- `spx/config.py`: shared constants, cache location, quirk-day list.
- `spx/cli/market.py`: `cmd_predict`, the daily prediction flow end to end.
- `spx/replica/pipeline.py`: stage-3 assembly and fusion, with the Nasdaq-vs-NYSE trust rationale in its docstring.
- `spx/model/fusion.py`: the inverse-variance combiner all flows converge on.
- `spx/strategy/data.py`: how market curves and model output join for the simulator.
