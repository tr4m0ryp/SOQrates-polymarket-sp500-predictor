# CLI Commands

Every command runs from the repo root as `python3 . <command> [flags]`. The entry chain is
`__main__.py` -> `open_predictor/cli/__init__.py` (`main()`, argparse with subparsers). Each subcommand
dispatches to a body in one of five files: `open_predictor/cli/market.py`, `open_predictor/cli/sources.py`,
`open_predictor/cli/auction.py`, `open_predictor/cli/newscmd.py`, `open_predictor/cli/strategy.py`.

Most commands read or build caches under `.cache/` (gitignored). Deleting a cache file forces
a rebuild. "Network" below means public HTTP endpoints reachable without a key unless a key
is named.

## Model: backtest, predict, quirks

Bodies in `open_predictor/cli/market.py`.

| Command | What it does | Prerequisites | Prints / writes |
|---|---|---|---|
| `backtest [--rebuild]` | Runs `open_predictor/forecast/backtest/run.py` train/test metrics on chronological halves | Network (Yahoo) on first build or `--rebuild`; else `.cache/dataset.json` | Metrics tables and quirk report to stdout; writes `.cache/dataset.json` |
| `predict` | Fits ModelV13 on the full dataset, reads live ES/NQ gaps, prints predicted official gap and P(up), compares to today's Polymarket odds | Network: Yahoo live futures + gamma-api.polymarket.com; dataset cache (auto-built) | Live gap, mu/sigma/P(up), Polymarket P(up), edge verdict |
| `quirks` | Lists quirk days (where the futures photo misleads) with safe/total count | Dataset cache (auto-built) | Quirk-day table via `run.quirk_report` |

## Data sources: ground-truth, weights, calendar-refresh

Bodies in `open_predictor/cli/sources.py`.

| Command | What it does | Prerequisites | Prints / writes |
|---|---|---|---|
| `ground-truth` | Audits Yahoo ^GSPC daily opens against stooq (tolerance 0.75 pts) | Network: Yahoo + stooq | Agreement line, or one line per disagreement day |
| `weights` | Loads S&P 500 constituent weights, sorts, shows Nasdaq-listed share | Network: Slickcharts + nasdaqlisted.txt (no key) | Constituent count, Nasdaq share %, top 10 by weight |
| `calendar-refresh` | Pulls CPI/PPI/NFP/GDP release dates from the FRED API | `FRED_API_KEY`; without it prints the NFP first-Friday fallback notice | Date counts per release; writes `.cache/releases.json` |

## Auction replica: lseg-*, databento-*, stage3, replica-sim, noii-deviation

Bodies in `open_predictor/cli/auction.py`.

| Command | What it does | Prerequisites | Prints / writes |
|---|---|---|---|
| `lseg-status` | Requests a DataScope Select auth token | `DSS_USERNAME` / `DSS_PASSWORD` | OK or failure reason |
| `lseg-pull --date D` | Pulls one quirk day of tick history for all constituents, caches the CSV, lists top FIDs seen | LSEG credentials, network, weights fetch | Writes `.cache/lseg/D.csv`; prints size and top 25 FIDs |
| `databento-status` | Metadata ping listing visible datasets | `DATABENTO_API_KEY` | Dataset count, XNAS.ITCH / XNYS.PILLAR presence |
| `databento-pull --date D` | Pulls one day of NOII/imbalance/prints/NBBO, caches raw JSON, lists observed DBN fields | `DATABENTO_API_KEY`, network | Writes `.cache/databento/D/`; prints record counts, errors, top 25 fields |
| `stage3 --date D [--source lseg\|databento]` | Replica-vs-official comparison: builds per-ticker predicted opens from a cached pull, runs the Monte Carlo distribution, compares to the official gap | A prior `databento-pull` or `lseg-pull` for D; network (Yahoo) for prior closes and ^GSPC. Default source: databento if `DATABENTO_API_KEY` set, else lseg | Replica gap, distribution mean/sigma/P(up)/quantiles, pivotal names, MATCH/MISS verdict |
| `replica-sim` | Synthetic self-test of the MC assembly: independent-case check vs analytic normal, a lumpy quirk scenario, print filtering | None (no data, no network) | Three scenario blocks to stdout |
| `noii-deviation --file F` | Parses a raw full-day `NASDAQ_ITCH50.gz` file up to the opening cross, aggregates NOII-vs-print deviations | The local ITCH file; weights fetch attempted but optional | Per-checkpoint deviation stats (median/mean/p90 bps, index signed, coverage), mega-cap detail |

## News layer: news-*

Bodies in `open_predictor/cli/newscmd.py`.

| Command | What it does | Prerequisites | Prints / writes |
|---|---|---|---|
| `news-mistakes [--rebuild]` | Inventories news-affected days where ModelProd was wrong or swung, labeled from `open_predictor/forecast/news/eval/event_labels.json` | Dataset cache (network on `--rebuild`) | Per-day table; writes `.cache/news_mistakes.json` |
| `news-timing` | Decisive-move-hour histogram across news days plus the derived LLM run schedule (02:30 to 09:15 ET) | `.cache/news_mistakes.json` from a prior `news-mistakes` run | Histogram, cumulative shares, schedule |
| `news-prefetch` | Builds tonight's Group-A context: releases, NFP flag, Polymarket baseline markets | Network (Polymarket, calendar) | Summary lines; writes `.cache/news_prefetch.json` |
| `news-groupb-fit` | Fits and reports Group-B constants: post-shock sigma ratio and conflicted-day direction hit-rate, train half only | Dataset cache | Per-half diagnostics plus the frozen `M_SHOCK` / `Z_CONFLICT` constants |
| `news-llm-test` | One live Group-B call with a canned test headline through the provider chain | `LLM_BASE_URL` + `LLM_API_KEY` + `LLM_MODEL` (optional `LLM_FALLBACK_*`); network | Provider name and the parsed JSON verdict |
| `news-llm-bench [--models a,b] [--verbose]` | Scores candidate models on the labeled cases in `open_predictor/forecast/news/eval/bench.py` | `LLM_API_KEY` (default base URL is NVIDIA's endpoint, override `LLM_BASE_URL`) | Score / valid-count / latency per model, winner line |
| `news-replay` | End-to-end replay: archived GDELT headlines per labeled day through the real Group-B prompt, scored against the decisive move | LLM env keys, network (GDELT), dataset cache | Per-day verdict lines, summary counts; writes `.cache/news_replay.json` |

## Strategy lab: pm-history, strategy-*

Bodies in `open_predictor/cli/strategy.py`.

| Command | What it does | Prerequisites | Prints / writes |
|---|---|---|---|
| `pm-history [--refresh]` | Fetches every resolved "SPX Opens Up or Down" market (series 10945) and its UP-token minute price curve | Network: gamma-api.polymarket.com | Writes `.cache/pm_history/<date>.json` per day; per-day fetch log |
| `strategy-data [--rebuild]` | Joins pm-history curves with model P(up) per hour into per-day strategy records | `pm-history` run first; dataset cache | Writes `.cache/strategy_days.json`; day count, up/down split, train/test boundary |
| `strategy-run --family F [--params JSON] [--half train\|test\|all] [--json] [--days]` | Simulates one strategy family with given params via `open_predictor/trading/strategy/engine/sim.py` | `.cache/strategy_days.json` (auto-built if pm-history cache exists) | Metrics table, or JSON with `--json` |
| `strategy-search [--half H] [--top N]` | Coarse grid search over five families (hold, takeprofit, flow_flip, longshot, scale_in), ranked by total PnL | Same as `strategy-run` | Top-N table: pnl, roi, win%, days, sharpe, drawdown, params |

Train/test discipline: `strategy-data` and `strategy-run` split days chronologically in half;
default `--half train`. Do not tune on `test`.

## Where to look

- `open_predictor/cli/__init__.py`: the full argparse surface, every flag and default in one place
- `open_predictor/cli/market.py`: backtest / predict / quirks bodies, including the live-predict flow
- `open_predictor/cli/auction.py`: all vendor pulls and the stage3 comparison logic
- `open_predictor/cli/newscmd.py`: news commands plus the hardcoded LLM run schedule
- `open_predictor/cli/strategy.py`: strategy grids searched by `strategy-search`
- `open_predictor/forecast/news/llm/runner.py`: LLM env-variable contract (`LLM_*`, `LLM_FALLBACK_*`)
