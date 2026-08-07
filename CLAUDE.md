# SPX Official-Open Predictor

Predicts the official S&P 500 opening print (WSJ/S&P first index tick, 9:30 ET)
ahead of the futures-watching crowd on Polymarket's daily "SPX Opens Up or Down"
market. Model background, validated numbers, and roadmap live in project memory
(`spx-open-predictor-roadmap.md`), not here.

## Language & style

- Python 3.12+, stdlib-first (urllib/json/math). No pandas/numpy in core paths.
- matplotlib only inside plotting helpers.
- No C/C++/Rust: the system is network-bound, one prediction/day; per-second
  data only in the 9:28-9:30 window. Do not add compiled components.
- Files < 300 lines; split into the existing domain tree at repo root, never flat.
- Research plots live in `plots/`; run all commands from the repo root.

## Package map

- `data/` fetchers: Yahoo chart API (ES/NQ/YM/^GSPC/^VIX1D), stooq
  ground-truth cross-check, Slickcharts + nasdaqlisted.txt -> index weights.
- `macro/` release calendar: NFP computed (first Friday), CPI/PPI/GDP
  from the FRED release-dates API into `.cache/releases.json`.
- `model/` regime scaler + model cores (v1.2 ES-only, v1.3 adds
  VIX1D sigma + NQ spread) + inverse-variance fusion.
- `replica/` stage-3 auction assembly core: montecarlo (distributional first
  tick + pivotal names + print filtering), timing (per-stock print-delay
  model, venue priors until LSEG labels), assembly, deviation, pipeline.
  Vendor subpackages: `databento/` (primary), `lseg/` (fallback),
  `itch/` + `taq/` (raw-file parsers + public sample fetchers),
  `stitch/` (free live fallbacks: Webull NOII + Massive imbalance).
- `news/` LLM news layer: `sources/` (GDELT + Alpaca wires), `llm/`
  (provider runner, prompts, Group-B weight), `eval/` (mistake inventory,
  timing profile, replay, bench); prefetch + schedule jobs at package root.
- `pm/` Polymarket gamma-api client + edge calculator + price history.
- `backtest/` dataset builder (`.cache/dataset.json`) + metric runner.
- `strategy/` Polymarket trading-strategy sim: rules, sizing, execution,
  bootstrap confidence bands.
- `cli/` argument parsing + command bodies (market/sources/auction/news/strategy).
- `data_sourcing/` standalone WRDS probe (runs under `.venv-wrds`, not the
  package import graph).

## Commands

```
python3 . backtest [--rebuild]   # train/test metrics, quirk table
python3 . predict                # live P(up) now + Polymarket edge
python3 . ground-truth           # stooq-vs-yahoo official-open audit
python3 . weights                # index weights / Nasdaq share
python3 . calendar-refresh       # FRED release dates (FRED_API_KEY)
python3 . noii-deviation --file  # NOII-vs-print stats from raw ITCH
python3 . lseg-status            # check DSS_USERNAME/DSS_PASSWORD
python3 . lseg-pull --date D     # LSEG fallback: pull one day, cache, discover FIDs
python3 . databento-status       # check DATABENTO_API_KEY (metadata ping)
python3 . databento-pull --date D  # primary: pull one day, cache raw JSON, discover fields
python3 . stage3 --date D [--source {databento,lseg}]  # replica-vs-official (default databento if keyed)
```

## Environment keys (all optional until the corresponding feature is used)

- `DSS_USERNAME` / `DSS_PASSWORD` - LSEG DataScope Select (Tick History).
  Academic license = research only; production trading needs commercial data.
- `FRED_API_KEY` - release calendar (CPI/PPI/NFP/GDP); free from FRED.
  Without it the calendar falls back to the NFP first-Friday rule.
- `MASSIVE_API_KEY` - live NYSE imbalance websocket leg.
- `DATABENTO_API_KEY` - primary auction source (stage-3 default): historical
  NOII/imbalance/prints/NBBO via stdlib HTTP+JSON; live via optional
  `pip install databento`. LSEG + the free-stitch modules are fallbacks.
- Weights come from Slickcharts + nasdaqlisted.txt (no key); iShares CSV is
  the fallback and currently serves a bot-wall.

## Conventions

- All timestamps ET (`America/New_York` zoneinfo); gaps in % of prior close.
- Train/test = chronological halves; never fit on the test half.
- Official-open ground truth: Yahoo ^GSPC daily open, cross-checked vs stooq;
  disagreement days are listed by `ground-truth` and excluded from fits.
- Cache under `.cache/` (gitignored); delete to force rebuild.
