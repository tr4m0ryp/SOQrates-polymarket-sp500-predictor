# Polymarket and the Strategy Lab

Two packages sit between the model and actual money. `open_predictor/trading/polymarket/` talks to
Polymarket: it finds the daily "SPX Opens Up or Down" market, turns the model
probability into a trade/no-trade verdict, and archives every past day's
minute-level price curve. `open_predictor/trading/strategy/` is the offline lab built on that
archive: a per-day dataset joining market prices with model output, a
simulator with an explicit execution-cost model, a registry of nine trading
rules, and a bootstrap analysis layer that puts confidence bands on bankroll
curves.

## Polymarket client (`open_predictor/trading/polymarket/`)

`open_predictor/trading/polymarket/gamma.py` fetches today's market from the gamma API by slug
(`spx-opens-up-or-down-on-<month>-<day>-<year>`). `open_market(date)` returns
the UP price, volume, liquidity, and the UP outcome's CLOB token id. Pure
stdlib urllib, no keys.

`open_predictor/trading/polymarket/edge.py` is the live decision rule used by `python3 . predict`.
`assess(p_model, p_market)` stands down when model confidence is below
`CONF_COMMIT` (0.65, from `open_predictor/config.py`), otherwise recommends BUY UP or
BUY DOWN when the model-vs-market divergence reaches `EDGE_THRESHOLD` (0.05).

`open_predictor/trading/polymarket/history.py` builds the research archive. `list_markets()` pages
through all closed events of series 10945 and keeps resolved days (UP price
settled at exactly 0 or 1). `fetch_all()` then pulls the UP token's minute
curve from the CLOB `prices-history` endpoint in 20-hour chunks (longer spans
return empty) and caches one JSON per day under `.cache/pm_history/`. CLI:
`python3 . pm-history [--refresh]`.

One caveat drives much of the simulator's design: prices-history returns CLOB
book midpoints, not trades. A dense curve exists even on days with $0 traded
volume, so a naive backtest fills orders that could never have executed.

## Strategy dataset (`open_predictor/trading/strategy/data.py`)

`build()` joins each cached market day with the backtest dataset row and a
`ModelProd` fit on the train half of the model dataset. Each record carries:
the outcome, official gap, traded volume, hourly ES gaps, the minute curve
clipped to 00:00 through 9:29 ET (`LAST_MINUTE` = 9:29, last tradeable
minute), and per-hour model output (P(up), mu, sigma). Cached at
`.cache/strategy_days.json`; `split()` cuts chronological halves. CLI:
`python3 . strategy-data [--rebuild]`.

Three signal variants are available to every rule via
`model_p_at(day, minute, signal)`: `model` (futures model alone), `news`
(plus the deterministic Group-B overlay from `open_predictor/forecast/news/llm/groupb.py`,
computed in `_news_p` with no look-ahead), and `llm` (plus replayed LLM
voices from `.cache/news_voice.json`, fused at checkpoints 04:00, 07:00,
8:35). `market_p_at` returns the latest quote at or before a minute.

## Sim engine (`open_predictor/trading/strategy/engine/`)

`sim.py` runs one rule over the day list. Two modes: flat $100 research
stakes, or bankroll compounding when params carry `bet_frac` or `stake_abs`
(start $100, never leveraged, ruin below $1 stops the run). Liquidity realism
gates: days with volume below `MIN_VOLUME` ($1000) are skipped entirely, and
the per-day stake is capped at `LIQ_FRAC` (1%) of real traded volume via the
`_avail` param the engine injects. Metrics per run: total pnl, ROI, win rate,
average payout multiplier, daily Sharpe, max drawdown, and final/min bankroll
in compounding mode.

`execution.py` models costs. Taker fee is Polymarket Fee Structure V2:
`shares * 0.04 * p * (1-p)` since 2026-03-30, makers pay zero. `ExecModel`
adds a half spread (default 0.01) and price impact per $100 of stake (default
0.005) on both entry and exit. `maker_fill` finds the first minute a resting
limit could fill, but since the curve is midpoints this is an optimistic
upper bound, and zero-volume days never fill.

`sizing.py` implements `optimal_stake`: on a thin book the multiplier decays
with stake, so it grid-searches $10 to $500 for the stake maximizing expected
profit under the execution model, returning None if no stake has positive EV.
Rules opt in with `{"sizing": "optimal"}`.

## Strategy families (`open_predictor/trading/strategy/rules/`)

`base.py` defines the shared plumbing (entry helper, edge-side test, stake
selection) and eight rules; each takes `(day, em, params)` and returns closed
trades. The `STRATEGIES` dict at the bottom of `base.py` is the registry the
engine and CLI dispatch on:

- `hold`: enter once at a fixed hour on edge >= 0.05 with a traded-side
  confidence gate, hold to resolution; `maker=1` posts a resting limit.
- `flow_flip`: ride the market favourite when the model agrees, reverse late
  if the model diverges hard.
- `takeprofit`: `hold` but sell into strength at a target token price.
- `longshot`: buy the cheap side (<= 0.15) when the model gives it >= 0.30.
- `scale_in`: clip in each hour the edge persists, dump all if the model flips.
- `convergence`: uses `crowd.py`, which fits a per-hour sigma to how the
  market prices the live ES gap (P(up) ~ Phi(gap/sigma), train half only,
  cached at `.cache/crowd_fit.json`). Enter on edge, exit into the forecast
  crowd repricing instead of carrying resolution risk.
- `dip_buy`: decide the side early, then wait for the token to dip below its
  decide-time price before entering.
- `first_signal`: enter at the first hour in a window that clears edge plus
  gate; `fresh_only=1` isolates late-clarifying days.

`composite.py` adds `full_strategy`, the designed production strategy from
`docs/research/approach.tex`: first-signal entry with a price cap (skip tokens above
0.90, where one quirk loss needs ~20 wins to repay), then monitors at 8:35
and 9:00 that sell when the live signal drops below `exit_thr` and can flip
the proceeds into the other side.

CLI: `python3 . strategy-run --family F --params '{...}' [--half test]` for
one config, `python3 . strategy-search` for a coarse grid over five families
ranked by pnl (grids live in `open_predictor/cli/strategy.py`).

## Analysis (`open_predictor/trading/strategy/analysis/`)

`bootstrap.py` answers how much of a bankroll curve is luck. For each of
three headline configs (first-signal flat $50, hour-4 hold at 10% of
bankroll, hour-4 hold flat $50) it extracts stake-independent per-day
contracts (side, token price, win, volume) from one canonical sim run,
asserts an identity replay matches `sim.run` to the cent, then replays the
staking rule over 10,000 day sequences resampled with replacement (seed
20260719). Output: 5/50/95 percentile bands per day plus terminal-wealth
percentiles, written to `.cache/bootstrap_bands.json`. Not wired into the
CLI; run `bootstrap.main()` from a Python one-liner.

`plot.py` holds all matplotlib. `bankroll_band()` draws the two headline
records with their 5-95% bootstrap bands into
`docs/research/plots/strategy_bankroll_50_band.png` (plus PDF).
`bankroll_trajectories()` draws raw $50/day vs guarded min($50, 20% of
bankroll) into `docs/research/plots/strategy_bankroll_50.png`; its title records
the test half (Apr 16 to Jul 14, 2026, 21 trades, 19W-2L) with the two loss
days annotated (Jul 2 news reversal, Jul 10 quirk day).

## Where to look

- `open_predictor/trading/strategy/rules/base.py`: all eight base rules and the `STRATEGIES` registry.
- `open_predictor/trading/strategy/engine/sim.py`: the day loop, volume gate, compounding, metrics.
- `open_predictor/trading/strategy/engine/execution.py`: fees, spread, impact, maker-fill caveat.
- `open_predictor/trading/strategy/data.py`: the day record schema and the three signal variants.
- `open_predictor/trading/polymarket/history.py`: how the market archive is built and its midpoint caveat.
- `open_predictor/trading/strategy/analysis/bootstrap.py`: the resampling design and headline configs.
