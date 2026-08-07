# 05 · Implementation status

What exists in the repo as of 2026-07-18.

## Built & verified

**Databento integration** (`spx/replica/databento/`) — Fable-verified **CONFIRMED**:
- `client.py` — auth + `get_range` (historical HTTP+JSON) + live entrypoint.
- `schemas.py` — DBN field maps + `normalize_imbalance/trade/quote` + `discover()`.
- `historical.py` — `nasdaq_noii`, `nyse_imbalance`, `cross_prints`, `nbbo_quotes`.
- `live.py` — `stream_imbalance` via optional `databento` SDK (lazy import).
- `source.py` — pipeline adapter: `pull_day`, `snapshots(date)` (lseg-shape),
  `prints(date)` → `{ticker: (px, ts_ns)}` for the timing model.
- Prices normalized from fixed-point nanodollar ints; ET timestamps.

**Free-stitch modules** (fallbacks, from the earlier build):
- `spx/replica/stitch/webull.py` — Webull OpenAPI NOII snapshot (free Nasdaq live).
- `spx/data/alpaca.py` — Alpaca auctions (#3) + quotes (#4).
- `spx/replica/itch/samples.py` — emi.nasdaq.com sample fetcher → `spx/replica/itch/parse.py`.
- `spx/replica/taq/samples.py` — ftp.nyse.com sample fetcher → `spx/replica/taq/parse.py`.
- `spx/replica/stitch/feeds.py` — Massive live NYSE imbalance websocket (completed stub).
- `spx/news/sources/alpaca.py` — Alpaca live news wire.

## Wired (CLI + config)

```
python3 . databento-status              # check DATABENTO_API_KEY (metadata ping)
python3 . databento-pull --date D       # pull one day, cache raw JSON, discover fields
python3 . stage3 --date D [--source {databento,lseg}]   # default databento if keyed
```

`DATABENTO_API_KEY` documented in `CLAUDE.md`. LSEG + free-stitch remain fallbacks.

## Pending

- **WRDS fetcher** — not built. Turns WRDS access into a free backtest for #2/#3/#4.
- **IBKR live client** — not built. The production live leg (both venues, tick 225).
- **News-layer slots** — earnings-tonight, nowcast+consensus, live wire (`alpaca_stream`
  exists but unwired into the schedule).

## Day-1 activation checklists

**Databento (when payment clears):**
1. `export DATABENTO_API_KEY=<key>`
2. `python3 . databento-status` → expect XNAS.ITCH: True, XNYS.PILLAR: True
3. `python3 . databento-pull --date <recent day>` → check non-zero record counts; review
   `discover()` field list (confirm `ref_price / cont_book_clr_price / auct_interest_clr_price
   / ind_match_price / paired_qty / total_imbalance_qty`; extend `schemas.py` only if a name
   differs).
4. Confirm the opening-cross flag in `trades` (currently earliest-priced-trade heuristic).
5. `python3 . stage3 --date <same day>` → ~500 tickers, replica-vs-official MATCH line.
6. Feed `{date: source.print_delays(date)}` into `TimingModel.fit_from_prints`.

**WRDS (once fetcher built):** connect via WRDS Python API → pull TAQ imbalance + trades +
NBBO for the constituent set + date → emit `snapshots`/`prints` → `stage3 --source wrds`.

**IBKR (once client built):** run IB Gateway, subscribe the right market-data lines (Nasdaq
TotalView + NYSE depth), `reqMktData(genericTick=225)` on constituents 9:28–9:30 → normalize.

## Known field/schema unknowns to confirm on first real pull

- Databento `imbalance` exact field names per venue (esp. whether NYSE PILLAR populates
  `ind_match_price` vs `cont_book_clr_price` — drives `pred_open` selection).
- Symbol presence in historical JSON (may need `map_symbols`/symbology).
- Opening-cross identifier in `trades` (distinct action/flag vs earliest-priced heuristic).
