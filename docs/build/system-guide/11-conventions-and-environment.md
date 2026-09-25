# Conventions and Environment

House rules for working in this repo: layout, language constraints, data conventions, the cache, and every environment key. Source of truth is `CLAUDE.md` at the repo root; this page adds detail found in the code.

## Three root directories, no more

The repo root holds exactly three directories, and `CLAUDE.md` forbids adding a fourth:

- `open_predictor/` all source code, grouped by role: `sources/` (`market/`, `macro/`), `forecast/` (`model/`, `news/`, `auction/`), `trading/` (`polymarket/`, `strategy/`), `evaluation/` (`backtest/`), `cli/`, plus `open_predictor/config.py` for shared constants.
- `scripts/` standalone scripts outside the import graph, by role: `data/` (`backfill.py`, `wrds_probe.py`), `evaluation/` (`stage3_eval.py`, `futures_baseline.py`), `checks/` (`selfcheck.py`).
- `docs/` all writing: `build/` (`system-guide/`, these pages; `data-vendors/`, the data-sourcing knowledge base), `tasks/` (open work items), `research/` (`approach.tex`, `paper/`, `plots/`, `figures/`).

Entry point is `__main__.py` at the root, so every command is `python3 . <command>` run from the repo root.

## Language and style

- Python 3.12+, stdlib-first: `urllib`, `json`, `math`. No pandas or numpy in core paths.
- matplotlib is allowed only inside plotting helpers.
- No C, C++, or Rust. The system is network-bound and makes one prediction per day; per-second data only in the 9:28 to 9:30 window. Do not add compiled components.
- Files stay under 300 lines. When a module grows, split it into the existing domain tree inside `open_predictor/`, never as flat siblings.
- Research plots go to `docs/research/plots/`.

## Data conventions

- All timestamps are ET, `ZoneInfo("America/New_York")`, defined once as `NY` in `open_predictor/config.py`.
- Gaps are expressed in percent of the prior close, everywhere.
- Train/test split is chronological halves. Never fit on the test half.
- Official-open ground truth is the Yahoo `^GSPC` daily open, cross-checked against stooq. `python3 . ground-truth` lists disagreement days, which are excluded from fits.
- Model constants (attenuation `K_DEFAULT = 0.767`, EWMA decay 0.94, confidence gate `CONF_COMMIT = 0.65`, the quirk-day list, and others) live in `open_predictor/config.py`, not scattered through the code.

## The `.cache/` directory

`open_predictor/config.py` creates `.cache/` at the repo root on import. It is gitignored (first line of `.gitignore`). Everything in it is derived data: delete a file, or the whole directory, to force a rebuild on the next run.

Files and subdirectories written by the package:

| Path | Written by |
|---|---|
| `.cache/dataset.json` | `open_predictor/evaluation/backtest/` dataset builder (`python3 . backtest --rebuild`) |
| `.cache/releases.json`, `releases_manual.json` | `open_predictor/sources/macro/releases.py` (FRED calendar) |
| `.cache/weights.json` | index-weights fetcher in `open_predictor/sources/market/` |
| `.cache/crowd_fit.json`, `print_delays.json`, `bootstrap_bands.json`, `strategy_days.json` | model, replica timing, and strategy fits |
| `.cache/news_*.json`, `.cache/news_llm_replay/` | `open_predictor/forecast/news/` prefetch, timing, replay, mistakes |
| `.cache/pm_history/` | Polymarket price history (`open_predictor/trading/polymarket/`) |
| `.cache/databento/`, `.cache/lseg/`, `.cache/itch/`, `.cache/nyse_taq/` | vendor pulls under `open_predictor/forecast/auction/vendors/` |
| `.cache/wrds_probe.json` | `scripts/data/wrds_probe.py` |

## Environment keys

All keys are optional until the corresponding feature is used. None are required for `backtest` or `predict` on cached data.

| Key | Unlocks | Read in |
|---|---|---|
| `FRED_API_KEY` | CPI/PPI/NFP/GDP release calendar (free from FRED). Without it, the calendar falls back to the computed NFP first-Friday rule. | `open_predictor/sources/macro/releases.py` |
| `DATABENTO_API_KEY` | Primary auction source, stage-3 default: historical NOII, imbalance, prints, NBBO via stdlib HTTP+JSON. Live feed needs an optional `pip install databento`. | `open_predictor/forecast/auction/vendors/databento/client.py` |
| `DSS_USERNAME` / `DSS_PASSWORD` | LSEG DataScope Select tick history, the auction fallback. Academic license is research-only; production trading needs commercial data. | `open_predictor/forecast/auction/vendors/lseg/tick_history.py` |
| `MASSIVE_API_KEY` | Live NYSE imbalance websocket leg in the free-stitch fallback. | `open_predictor/forecast/auction/vendors/stitch/feeds.py` |
| `NCDS_CLIENT_ID` / `NCDS_CLIENT_SECRET` | Nasdaq NOII leg of the same free-stitch fallback. | `open_predictor/forecast/auction/vendors/stitch/feeds.py` |
| `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` | The news layer's LLM runner. Any OpenAI-compatible chat-completions endpoint works (Gemini compat, Groq, OpenRouter, DeepSeek). All three must be set. Budget is about 12 calls per night, sized to fit free tiers. | `open_predictor/forecast/news/llm/runner.py` |
| `LLM_FALLBACK_BASE_URL` / `_API_KEY` / `_MODEL` | Optional second provider, tried in order on failure. | `open_predictor/forecast/news/llm/runner.py` |
| `ALPACA_API_KEY` / `ALPACA_API_SECRET` | Alpaca news wire (free key) for the news layer, plus a market-data helper in `open_predictor/sources/market/alpaca.py`. | `open_predictor/forecast/news/sources/alpaca.py`, `open_predictor/sources/market/alpaca.py` |

Index weights need no key: Slickcharts plus `nasdaqlisted.txt`, with the iShares CSV as a fallback that currently serves a bot-wall.

Status commands to verify credentials: `python3 . lseg-status`, `python3 . databento-status`.

## WRDS probe

`scripts/data/wrds_probe.py` is a standalone script outside the `open_predictor` import graph. It checks which WRDS (Wharton Research Data Services) tables this project can actually read: ground-truth index opens (Compustat `idx_daily`, CRSP `dsp500`), constituent membership and venue tags, CBOE volatility tables, IBES surprises, and TAQ libraries where denial is expected and documents the gap. Results go to `.cache/wrds_probe.json` per table: exists, readable, row count, columns, date coverage.

It runs under a dedicated virtualenv because the `wrds` client drags in pandas, which the main package bans:

```
.venv-wrds/bin/python scripts/data/wrds_probe.py
```

The venv is not committed and does not currently exist in this checkout; create it and install `wrds` before running. Authentication needs a one-time `~/.pgpass` entry: `.venv-wrds/bin/python -c "import wrds; wrds.Connection().create_pgpass_file()"`.

## Where to look

- `CLAUDE.md` root file with the layout rule, style rules, commands, and keys.
- `open_predictor/config.py` shared constants, ET zoneinfo, cache root, model parameters, quirk days.
- `.gitignore` what stays out of git: `.cache/`, LaTeX build output, PDFs.
- `open_predictor/forecast/news/llm/runner.py` LLM provider configuration and fallback chain.
- `open_predictor/forecast/auction/vendors/stitch/feeds.py` free-stitch feeds and their keys.
- `scripts/data/wrds_probe.py` the WRDS dataset probe and its candidate table list.
