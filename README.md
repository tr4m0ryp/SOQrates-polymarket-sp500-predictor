# sOQrates: SPX Official-Open Predictor

Predicts the official S&P 500 opening print (the 9:30 ET first index tick)
and prices it against Polymarket's daily "SPX Opens Up or Down" market. The
official open realizes only ~80% of the overnight futures gap while the crowd
prices ~100%; the model exploits that gap with futures, regime-aware
volatility, news, and opening-auction data. Stdlib-only Python 3.12+.
Status: research system with a working backtest and live predictor; the
trading record is promising but not yet statistically confirmed.

## Results

Out-of-sample, from the paper abstract (`docs/research/paper/sections/abstract.tex`):

| Prediction time | Accuracy | 95% CI | n |
|---|---|---|---|
| 00:00 ET | 72.5% | 66 to 78 | 200 |
| 00:00 ET, confident days only (P >= 65%) | 82.1% | | |
| 09:29 ET | ~94% | 74 to 99 | 18 |

- One of 15 fee- and execution-audited strategies survives: first confident
  hour entry turns $100 into $321.53 at flat $50 stakes (26 wins, 2 losses).
- White's reality check across the whole strategy family gives an adjusted
  p of 0.26 to 0.36, so the edge is **not yet confirmed**. Caveats: one market
  regime, 58 test days, a thinning market, a crowd that can learn.

## Quick start

Run everything from the repo root. No install needed for the core; API keys
are optional until a feature needs one (see `CLAUDE.md` -> Environment keys).

```
python3 . backtest          # train/test metrics + quirk-day table
python3 . predict           # live P(up) now + Polymarket edge
python3 . --help            # every command
python3 scripts/checks/selfcheck.py   # offline regression checks (CI-safe)
```

## Repository layout

Three root directories, each directory holding at most five entries:

```
open_predictor/          the importable package (entry: python3 .)
  cli/                   argument parsing + command bodies
  config.py              paths, quirk days, shared constants
  sources/               external inputs
    market/              Yahoo, stooq, Alpaca, index weights
    macro/               FRED / NFP release calendar
  forecast/              prediction layers
    model/               futures-gap model, regime scaler, fusion
    news/                LLM news layer (sources, llm, eval, ops)
    auction/             opening-auction replica (Databento, LSEG, ITCH/TAQ)
    backtest/            dataset builder + train/test metrics
  trading/               acting on the forecast
    polymarket/          gamma-api client, edge, price history
    strategy/            trading-strategy simulator
scripts/                 standalone runs outside the import graph
  data/                  capped Databento backfill, WRDS probe
  evaluation/            stage-3 replica evaluation, futures baseline
  checks/                offline regression self-check
docs/
  build/
    system-guide/        onboarding: overview, architecture, commands
    data-vendors/        auction-data vendors and the decided stack
  tasks/                 open work items and their designs
  research/              approach.tex, paper/ (Overleaf mirror), plots/, figures/
```

New here? Read `docs/build/system-guide/README.md`, then pages 01, 02, and 09.
Contributor rules (coding standards, directory discipline) are in `CLAUDE.md`.

## License

SPX Open Predictor is **source-available**, licensed under the
[PolyForm Noncommercial License 1.0.0](./LICENSE), **not** an OSI
open-source license.

- **You may** use, modify, fork, and share SPX Open Predictor freely for any
  **noncommercial** purpose, as long as you keep the copyright and
  `Required Notice:` lines (see [`NOTICE`](./NOTICE)) and credit
  *"SPX Open Predictor by Keygraph, Inc."*
- **You may not** sell it, bundle it into a paid product, or run it as a
  paid/hosted service **without a commercial license**.

Copyright (c) 2026 Keygraph, Inc. Commercial licensing enquiries: see
[`NOTICE`](./NOTICE).
