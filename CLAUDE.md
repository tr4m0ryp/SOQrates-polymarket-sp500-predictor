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
- Files < 300 lines; split into the existing package tree, never flat.

## Package map

- `spx_open/data/` fetchers: Yahoo chart API (ES/NQ/YM/^GSPC/^VIX1D), stooq
  ground-truth cross-check, IVV holdings -> index weights.
- `spx_open/macro/` release calendar: NFP computed (first Friday), CPI/PPI
  fetched from BLS schedule pages into `.cache/releases.json`.
- `spx_open/model/` regime scaler + model cores (v1.2 ES-only, v1.3 adds
  VIX1D sigma + NQ spread) + inverse-variance fusion.
- `spx_open/replica/` stage-3 auction first-tick assembly; Databento wrapper
  reads `DATABENTO_API_KEY` env (untested until a key is provided).
- `spx_open/pm/` Polymarket gamma-api client + edge calculator.
- `spx_open/backtest/` dataset builder (`.cache/dataset.json`) + metric runner.

## Commands

```
python3 -m spx_open backtest [--rebuild]   # train/test metrics, quirk table
python3 -m spx_open predict                # live P(up) now + Polymarket edge
python3 -m spx_open ground-truth           # stooq-vs-yahoo official-open audit
python3 -m spx_open weights                # index weights / Nasdaq share
python3 -m spx_open calendar-refresh       # FRED release dates (FRED_API_KEY)
python3 -m spx_open noii-deviation --file  # NOII-vs-print stats from raw ITCH
python3 -m spx_open lseg-status            # check DSS_USERNAME/DSS_PASSWORD
python3 -m spx_open lseg-pull --date D     # pull one day, cache, discover FIDs
python3 -m spx_open stage3 --date D        # replica-vs-official for cached day
```

## Environment keys (all optional until the corresponding feature is used)

- `DSS_USERNAME` / `DSS_PASSWORD` - LSEG DataScope Select (Tick History).
  Academic license = research only; production trading needs commercial data.
- `FRED_API_KEY` - release calendar (CPI/PPI/NFP/GDP); free from FRED.
  Without it the calendar falls back to the NFP first-Friday rule.
- `MASSIVE_API_KEY` - live NYSE imbalance websocket leg.
- `DATABENTO_API_KEY` - optional alternative historical/live source.
- Weights come from Slickcharts + nasdaqlisted.txt (no key); iShares CSV is
  the fallback and currently serves a bot-wall.

## Conventions

- All timestamps ET (`America/New_York` zoneinfo); gaps in % of prior close.
- Train/test = chronological halves; never fit on the test half.
- Official-open ground truth: Yahoo ^GSPC daily open, cross-checked vs stooq;
  disagreement days are listed by `ground-truth` and excluded from fits.
- Cache under `.cache/` (gitignored); delete to force rebuild.
