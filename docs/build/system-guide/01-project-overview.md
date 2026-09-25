# Project Overview: SPX Open Predictor (sOQrates)

GitHub repo: `tr4m0ryp/sOQrates`. The research paper built from this repo is titled
"SOQrates: Predicting the S&P 500 Opening Price"
(`docs/research/paper/main.tex`). The name puns on the SOQ, the
Special Opening Quotation used to settle index futures, which this project
explicitly does not predict.

## What it predicts

The official S&P 500 opening print: the first index value S&P publishes at
9:30:00 ET, compared against the prior official close. This is a calculation,
not a traded price. S&P recomputes the index on roughly a five-second interval
from each constituent's last price. Stocks that have not opened yet are carried
at their prior close, and the first published value is never restated. The
index holds roughly 505 names and 57.5% of its weight is Nasdaq-listed.
Nasdaq stocks cross at exactly 9:30:00 and print immediately; NYSE opens are
run by designated market makers and lag by seconds to minutes, so the NYSE
half of the index enters the first tick stale. On days decided by 0.1 to 0.2
index points, which individual stocks were counted live can be the whole answer.

## The market it trades against

Polymarket runs a daily binary market, "SPX Opens Up or Down" (series 10945,
slug `spx-open-daily-up-or-down`), that resolves on the official opening print
versus the prior close; ties resolve 50/50. Volume ran near $664k per day in
January 2026 and declined to roughly $30k to $48k per day by July 2026. The
Polymarket client lives in `open_predictor/trading/polymarket/gamma.py` and the edge calculator in
`open_predictor/trading/polymarket/edge.py`.

## The core idea

Nearly everyone in that market watches the overnight gap in the E-mini S&P 500
futures (ES) and prices the market as if that gap carries into the official
open in full: pass-through k = 1, noise zero. Measured over 200 trading days,
only about 80% of the gap survives into the official open (k roughly 0.767 to
0.797). The model is a frozen linear map: predicted gap = a0 + k * g, with g
the ES futures gap and a0 = 0.0092%, wrapped in a fitted width sigma(tau) that
decays from plus or minus 0.344% at midnight to plus or minus 0.083% at 9:29.
That 20% spread, plus the predictable shrinking of the noise, is the entire
edge. The cost of the crowd's error concentrates on auction-quirk days,
roughly one per month, when ES holds its direction and the official print
lands opposite or nearly flat.

## Model versions

Both cores live in `open_predictor/forecast/model/core.py`:

- **v1.2**: ES-only. The linear gap map plus the time-decaying width.
- **v1.3**: adds a VIX1D-based sigma and the NQ (Nasdaq futures) spread as
  inputs. Combined with v1.2 by inverse-variance fusion in
  `open_predictor/forecast/model/fusion.py`, with a regime scaler in `open_predictor/forecast/model/regime.py`.

Train/test splits are chronological halves and the model is fitted once and
never refit on the test half (`open_predictor/forecast/backtest/`).

## Headline results (paper abstract)

From `docs/research/paper/sections/abstract.tex`:

- Out-of-sample accuracy is a ladder, not a number: 72.5% at midnight
  (95% CI 66 to 78, n = 200), rising to roughly 94% at 9:29 (95% CI 74 to 99,
  n = 18).
- Standing down on coin-toss days (midnight confidence below 65%) lifts
  committed midnight accuracy to 82.1%.
- A fee- and execution-audited backtest leaves one survivor of 15 strategy
  candidates: entering at the first confident hour turns $100 into $321.53 at
  flat $50 stakes, 26 wins against 2 losses (93%, 95% CI 77 to 98). The
  hour-4 hold variant reaches $135.92 staking 10% of bankroll per trade.
- White's reality check, which prices in that this is the best of the
  candidate family, gives an adjusted p of 0.26 to 0.36 against a naive 0.03.
  The trading record is promising but statistically unconfirmed.
- Standing caveats: one market regime, 58 test days, a thinning market, a
  crowd that can learn.

## Status and stack

Stdlib-only Python 3.12+ (urllib/json/math, no pandas or numpy in core paths),
one prediction per day, network-bound. Entry point is `__main__.py`; run
`python3 . backtest` or `python3 . predict` from the repo root. Beyond the
day-level core, `open_predictor/forecast/auction/` builds a stage-3 replica of the opening auction
(per-stock print timing, Monte Carlo first-tick distribution) fed by Databento
as the primary source and LSEG as fallback. Licensed PolyForm Noncommercial
1.0.0 by Keygraph, Inc. (`LICENSE`, `NOTICE`).

## Where to look

- `README.md`: two-line pitch, commands, license.
- `CLAUDE.md`: package map, commands, environment keys, conventions.
- `docs/research/paper/sections/abstract.tex`: headline numbers.
- `docs/research/paper/sections/introduction.tex`: market
  mechanics, crowd error, the five claimed contributions.
- `open_predictor/forecast/model/core.py`: the v1.2 and v1.3 model cores.
- `open_predictor/trading/polymarket/edge.py`: model probability versus Polymarket price.
