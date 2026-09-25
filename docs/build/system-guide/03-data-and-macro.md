# Data and Macro Layer

Everything in `open_predictor/sources/market/` and `open_predictor/sources/macro/` is stdlib-only Python (urllib, json,
csv). There are no API client libraries in these paths. All fetchers share two
constants from `open_predictor/config.py`: `NY` (the `America/New_York` zoneinfo used for
every timestamp) and `CACHE` (the gitignored `.cache/` directory at repo root,
created on import). `LOOKBACK_DAYS = 720` caps the hourly history window
because Yahoo's 60m endpoint serves roughly 730 days.

Quick reference:

| Module | Source | Cache file | Env key |
|---|---|---|---|
| `open_predictor/sources/market/yahoo.py` | Yahoo v8 chart API | none | none |
| `open_predictor/sources/market/futures.py` | Yahoo (via `yahoo.py`) | none | none |
| `open_predictor/sources/market/ground_truth.py` | stooq.com daily CSV | none | none |
| `open_predictor/sources/market/weights.py` | Slickcharts + nasdaqtrader.com | `.cache/weights.json` | none |
| `open_predictor/sources/market/alpaca.py` | Alpaca Market Data v2 | none | `ALPACA_API_KEY` / `ALPACA_API_SECRET` |
| `open_predictor/sources/macro/releases.py` | FRED release-dates API | `.cache/releases.json` | `FRED_API_KEY` (fallback works without) |

Both `open_predictor/sources/market/__init__.py` and `open_predictor/sources/macro/__init__.py` are empty; import the
submodules directly.

## open_predictor/sources/market/yahoo.py

Hits `https://query1.finance.yahoo.com/v8/finance/chart/{symbol}` with a
Mozilla User-Agent, 60s timeout, and 4 retries with linear backoff. Three
functions: `chart(symbol, interval, days_back)` returns raw timestamps, closes,
and the full result blob; `hourly_closes()` returns a dict keyed by bar END
time (bar start + 3600) to close; `daily_open_close()` returns ET-date string
to (open, close). Nothing is cached here; callers cache derived data.

## open_predictor/sources/market/futures.py

Builds `HourlyFeed` objects for `ES=F`, `NQ=F`, `YM=F` from Yahoo hourly
closes. `price_at(utc_ts)` does a bisect lookup with a 3900s staleness
tolerance. `gap_path(feed, date, prior_date)` returns the percent gap versus
the prior day's 16:00 ET price at each hour 0 through 9 of the target date;
this is the model's main input. `prior_day_rv()` sums squared hourly returns
from 10:00 to 16:00 ET as a realized-variance proxy, and `live_gap()` gives
the current gap for the live predict path.

## open_predictor/sources/market/ground_truth.py and the ground-truth rule

Official-open ground truth is Yahoo `^GSPC` daily open, cross-checked against
stooq. `stooq_daily()` downloads the full `^spx` daily history as CSV from
`https://stooq.com/q/d/l/?s=%5Espx&i=d`. `audit(days_back=330, tol_pts=0.75)`
returns every date where the two sources disagree on the open by more than
0.75 index points. `python3 . ground-truth` (wired in `open_predictor/cli/sources.py`)
prints the disagreement list.

One caveat: the project convention (see the repo `CLAUDE.md`) says disagreement
days are excluded from fits, but nothing in `open_predictor/forecast/backtest/dataset.py` or
`open_predictor/forecast/backtest/run.py` calls `audit()`. Exclusion is a manual step today. The
separate `QUIRK_DAYS` list in `open_predictor/config.py` (12 dates where ES held direction
but the official print went the other way) is only used for the quirk report in
`open_predictor/forecast/backtest/run.py`, not removed from training either.

## open_predictor/sources/market/weights.py and the index-weights pipeline

Three sources combine into one constituent table:

1. Weights come from the Slickcharts S&P 500 page
   (`https://www.slickcharts.com/sp500`), parsed with a regex over the plain
   HTML. The parse must yield at least 400 rows or it raises.
2. Listing venue comes from Nasdaq's official symbol directory
   (`https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt`), a
   pipe-separated file. A ticker present there (test issues excluded) is
   Nasdaq-listed, everything else is treated as NYSE. This matters because
   Nasdaq names cross at exactly 9:30:00 while NYSE opens lag.
3. Fallback: the iShares IVV holdings CSV. The endpoint currently serves a
   bot-wall, so it only runs if the Slickcharts parse throws.

**Header sensitivity, the failure mode that takes the whole system down.**
Both live hosts filter on request headers, and they disagree about what they
want. Slickcharts returns 403 to a bare `Mozilla/5.0` user agent and needs a
full browser UA string; nasdaqtrader returns 406 if `Accept` is html-only and
wants `*/*`. On 2026-08-12 the bare UA started failing, `load()` fell through
to the iShares bot-wall, and the whole chain died with a bare `StopIteration`
from the CSV header scan. Nothing downstream works without weights: no
Databento pull can build its symbol list, and the replica cannot weight
constituents. If you see `StopIteration` out of `weights.py`, the real cause
is upstream header rejection, not a malformed CSV. The current header set in
`_UA` satisfies both hosts; re-verify it before blaming anything else.

`load()` caches the result in `.cache/weights.json` for 5 days. Each row is
`{ticker, weight, exchange}`. `nasdaq_share()` computes the Nasdaq-listed
fraction of index weight. CLI: `python3 . weights`.

## open_predictor/sources/market/alpaca.py

Client for Alpaca Market Data v2 at `https://data.alpaca.markets/v2/stocks`.
Auth is `ALPACA_API_KEY` / `ALPACA_API_SECRET` from the environment, sent as
`APCA-API-KEY-ID` / `APCA-API-SECRET-KEY` headers. `auctions()` and `quotes()`
pull paginated historical opening/closing auction prints and NBBO quotes.
`official_open()` extracts, per symbol, the one opening print whose exchange
code matches the primary listing venue (Q for Nasdaq, N for NYSE, using the
venue names `weights.py` emits). `nbbo_at()` finds the quote nearest an ET
timestamp. `LiveIexQuotes` holds the auth/subscribe/normalize logic for the
free real-time IEX quote websocket (`wss://stream.data.alpaca.markets/v2/iex`);
streaming needs an optional `pip install websockets`, kept out of the REST
path. Cost note from the module docstring: the free tier gives real-time IEX
quotes only (no delay, contrary to the common claim), while SIP history
requires the $99/mo Algo Trader Plus plan. Nothing is cached.

## open_predictor/sources/macro/releases.py

The 8:30 ET macro-release calendar. `refresh()` needs `FRED_API_KEY` (free)
and pulls `https://api.stlouisfed.org/fred/release/dates` for four release
ids: CPI=10, PPI=46, NFP (Employment Situation)=50, GDP=53, going back 2
years and including scheduled future dates. Results are written to
`.cache/releases.json`. `_load()` merges in user-maintained overrides from
`.cache/releases_manual.json` if present. Without a key, `is_nfp_friday()`
(first Friday of the month) still works, so release-morning detection degrades
rather than breaks. The docstring warns that BLS schedule pages 403 scripted
fetches; do not re-add them. CLI: `python3 . calendar-refresh`.

## Who consumes this layer

`open_predictor/forecast/backtest/dataset.py` is the main consumer: it joins futures gap paths,
`^GSPC` daily open/close, `^VIX1D` prior close, prior-day RV, and the
`release_morning` flag into `.cache/dataset.json` (last 480 trading days).
`open_predictor/cli/market.py` uses `releases.is_release_morning()` on the live predict
path, and `open_predictor/forecast/news/` modules attach `release_names()` to news snapshots.

## Where to look

- `open_predictor/sources/market/yahoo.py`: the one HTTP wrapper every price fetch goes through
- `open_predictor/sources/market/futures.py`: gap paths and RV, the model's core inputs
- `open_predictor/sources/market/weights.py`: full weights pipeline including venue tagging
- `open_predictor/sources/market/ground_truth.py`: the Yahoo-vs-stooq audit
- `open_predictor/sources/macro/releases.py`: FRED calendar plus the no-key NFP fallback
- `open_predictor/forecast/backtest/dataset.py`: how it all lands in `.cache/dataset.json`
