# 03 · The decided stack

Most-reliable-and-cheapest single source per need.

## Historical (backtest / model fitting)

| Data | Source | Price | Note |
|---|---|---|---|
| Nasdaq NOII (#1) | **Databento** (filtered pulls) | ~$0–50 | The one WRDS gap; client built |
| NYSE imbalance (#2) | **WRDS · NYSE Daily TAQ imbalance** | **Free** | Arbitrary dates, ~2003+, ms |
| Cross print + ts (#3) | **WRDS · TAQ trades** | **Free** | Exact ts + venue → timing model |
| Constituent NBBO (#4) | **WRDS · TAQ NBBO** | **Free** | Consolidated ms |

Free stopgap for Nasdaq NOII if Databento stays blocked: free ITCH samples (limited dates),
or **self-record forward** via a live leg from today onward.

## Live (production)

**All four legs → one IBKR account** (tick 225 + L1), both venues, EU-reachable,
**~$17–40/mo total**. This beats the Webull-free + Massive-$49 stitch on **both** reliability
(official API, both venues, no region gamble, one account) **and** cost.

Alternative if avoiding IBKR: **Webull OpenAPI** (free, Nasdaq NOII only, `webull_noii.py`
built) **+ Massive** ($49/mo, NYSE only) — cheaper on the Nasdaq half, but two accounts,
Nasdaq access uncertain, and no cross-venue single API.

## News / macro layer (secondary)

| Data | Source | Price | Status |
|---|---|---|---|
| Macro release dates | FRED release-dates API | Free (key) | Running (NFP-only until key) |
| Consensus estimates | FMP economic calendar | Free tier | To wire |
| Earnings-tonight | FMP earnings calendar | Free tier | To wire |
| Live news wire | Alpaca news websocket | Free | To wire |

## Cost, decided

- **Backtest: ~$0** — WRDS covers 3 of 4 historical legs; Nasdaq NOII history = cheap Databento
  pull, or free via self-recording forward.
- **Live: ~$17–40/mo** — one IBKR account, both venues.

## What's left to build

Two adapters (the Databento client is already done and verified):

1. **WRDS fetcher** — pull NYSE imbalance + trades + NBBO via the WRDS Python/Postgres API,
   emit the `snapshots(date)` / `prints(date)` shapes stage3 + timing consume. Turns WRDS
   access into a working **$0 backtest immediately**; depends on no pending key.
2. **IBKR live client** — `ib_insync`, subscribe tick 225 on constituents in the 9:28–9:30
   window, normalize to the same dicts. The production live leg.

## Hard constraint

**WRDS is research-only** (academic license) — it validates the model and fits the parameters,
but **cannot legally power live production trading**. The live leg must come from a commercial
source (IBKR / Databento-live / Massive). Same caveat that applied to the LSEG academic route.
