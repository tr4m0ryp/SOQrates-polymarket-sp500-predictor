# Data sources — coverage, cost, and implementation status

Reference for the SPX official-open predictor. Rows above the divider are the core
model (running today); the **bold** rows are the auction layer (Track 3), the reason
we went looking at LSEG. Sources for the auction layer were selected by the
2026-07-17 deep-research run (104 agents, 22 sources, 20 verified claims).

## Decided stack — one pick per need (2026-07-18)

Most-reliable-and-cheapest single source per row. Detailed multi-option table below.

**Auction — HISTORICAL (backtest):**
- Nasdaq NOII → **Databento** (metered filtered pulls, ~$0–50; the one WRDS gap). Built, needs access.
- NYSE imbalance → **Databento** (WRDS route DEAD: UvA has no TAQ subscription, verified 2026-07-19).
- Cross print + ts → **Databento** / Massive free REST `/v1/open-close` (daily opens, no ts).
- Constituent NBBO → **Databento** / free IEX subset.

**Auction — LIVE (production):** all four legs → **IBKR** (tick 225 + L1, one EU-reachable
account, both venues), **~$17–40/mo total**. Beats Webull-free+Massive-$49 on reliability *and*
cost. To wire. (Webull OpenAPI = free Nasdaq-only alt, `open_predictor/forecast/auction/vendors/stitch/webull.py` already built.)

**News layer:** macro dates → FRED (free key); consensus + earnings → FMP free tier; live wire
→ Alpaca news WS (free). All to wire except FRED (running, NFP-only).

**Two adapters left to build:** WRDS fetcher (ground truth / weights / VIX / earnings — NOT
auction data) + IBKR live client (production). Databento client already built.
WRDS = research-only (no live/production trading).

**Legend — Sourced & runnable:** `Yes` = wired and running · `Partial` = running but
incomplete · `No` = not yet wired (Source column names the chosen one to build).

| Data we need | Sourced & runnable | Source | Price |
|---|---|---|---|
| S&P 500 futures (ES) level/gap | Yes | Yahoo chart API | Free |
| Nasdaq futures (NQ) — NQ–ES spread | Yes | Yahoo chart API | Free |
| Dow futures (YM) | Yes | Yahoo chart API | Free |
| S&P 500 index (^GSPC) open/close | Yes | Yahoo chart API | Free |
| 1-day VIX (^VIX1D) — sigma input | Yes | Yahoo chart API | Free |
| Independent official-open cross-check | Yes | stooq | Free |
| Index constituent weights | Yes | Slickcharts + nasdaqlisted.txt | Free |
| Per-constituent venue tag (Nas/NYSE) | Yes | nasdaqlisted.txt | Free |
| Polymarket prices / odds | Yes | Polymarket gamma-api | Free |
| News headlines + event timestamps | Yes | GDELT DOC 2.0 (keyless) | Free |
| LLM news classifier (direction/shock) | Yes | GitHub Models (gpt-4.1) / NVIDIA NIM | Free tier |
| Macro release calendar (CPI/PPI/GDP) | Partial | FRED release-dates API (NFP-rule fallback) | Free (key) |
| Earnings-tonight flag (heavyweights) | No | *unwired — prefetch slot TODO* | Free (TBD) |
| Nowcast + analyst consensus | No | *unwired — Cleveland Fed / consensus TODO* | Free |
| Real-time news wire stream | No | Alpaca news websocket (free key) | Free |
| **Nasdaq NOII — historical** | Partial | Free ITCH samples (limited dates); **not in WRDS TAQ** → Databento / self-record for arbitrary dates | Free (limited) |
| **Nasdaq NOII — live** | No | IBKR tick 225 (both venues, EU-reachable) / Webull | ~$17–40/mo · or free |
| **NYSE opening imbalance — historical** | No | ~~WRDS TAQ~~ (**no UvA subscription, verified 2026-07-19**) → Databento | metered |
| **NYSE opening imbalance — live** | No | IBKR tick 225 / Massive NOI WebSocket | ~$40/mo · or $49/mo |
| **Per-stock opening cross print + ts** | Partial | ~~WRDS TAQ~~ (no subscription) → Massive free REST daily opens (no ts) / Databento for ts | Free / metered |
| **Constituent quote midpoints (pre-open NBBO)** | No | ~~WRDS TAQ NBBO~~ (no subscription) → Databento; IBKR L1 / free IEX live | metered |

## Cost to operate

- **Validation / backtest:** **not $0** — the WRDS shortcut is gone (no TAQ at UvA). Both venues'
  auction history needs Databento (metered) or free ITCH/NYSE sample dates. WRDS still gives
  free official-open ground truth, constituent weights, VIX and earnings dates.
- **Go live:** **~$17–40/mo (IBKR)** — tick 225 gives both venues live, EU-reachable; or the
  free-ish Webull(Nasdaq)+Massive($49) stitch. WRDS is research-only and cannot power live trading.

## WRDS (access confirmed — but **TAQ is NOT included**, verified 2026-07-19)

**Correction of the 2026-07-18 assumption.** UvA's WRDS subscription does **not** include TAQ.
Verified two independent ways while logged in: the products page shows every `taq_*`/`taqm_*`
year unsubscribed (incl. `taqm_2025`, `taqm_2026`), and the TAQ query page returns
*"Sorry, you do not have access to this content … You must be subscribed to: taq_common,
taqm_common."* Only the **samples** (`taqsamp_all`, `taqmsamp_all`) are available.

- **Consequence:** WRDS gives us **none** of the auction legs. NYSE imbalance, cross prints
  and constituent NBBO revert to their pre-WRDS status — Databento (historical) / IBKR (live).
- Even with a TAQ subscription, WRDS TAQ lists only Consolidated Trades + Consolidated Quotes;
  whether it carries the NYSE Order-Imbalance file at all is unconfirmed — do not assume it.
- **What UvA *is* subscribed to that this project can use** (177 products total; probe via
  `.venv-wrds/bin/python scripts/data/wrds_probe.py` once `~/.pgpass` exists):
  `comp_na_daily_all` (Compustat NA daily — index daily prices incl. **open**, constituent
  membership), `crsp_a_stock`/`crsp_q_stock`, `crsp_a_indexes`, `crsp_a_ccm` (linking),
  `cboe_all` (VIX family daily), `tr_ibes` (earnings actuals + consensus), `frb_all` (Fed
  rates), `ff_all`, `wrdsapps_*`. No OptionMetrics (sample only), no Datastream (sample only),
  no futures.
- **Still research-only** (academic licence): validates the model, cannot power live trading.

## Known gaps / caveats

- Free `emi.nasdaq.com` ITCH sample dates are fixed and scattered (mostly 2019/2022) and
  rotate — they may not align with the specific quirk days the backtest wants.
- No free source of **arbitrary-date** historical NYSE imbalance; only the published NYSE
  sample dates are free.
- No fully-free option covers **live NYSE imbalance** — mitigated by Nasdaq-listed mega-caps
  dominating SPX weight (the free Webull Nasdaq-NOII leg captures the highest-signal names).
- **Massive free Basic tier confirmed (2026-07-18):** REST only, **no websocket**, so the NOI
  imbalance feed is unreachable — verified live (`auth_failed: "Your plan doesn't include
  websocket access"`). The NOI feed is the **Imbalances Expansion $49/mo** add-on, real-time
  only (no imbalance history at any tier). BUT the free Basic REST key *does* return official
  per-stock daily opens (`/v1/open-close`, grouped-daily) with 2yr history — a free source for #3.
- Databento would be the clean all-in-one (Nasdaq + NYSE, hist + live) but is card-blocked;
  its $125 free-credit "workaround" was adversarially refuted — do not rely on it.
- Kaggle / Hugging Face / Zenodo / GitHub public-dataset avenue surfaced nothing verified —
  unexplored, not ruled out.

## Implementation map (new/updated modules)

| Source | Module | State before |
|---|---|---|
| Alpaca auctions (#3) + quotes (#4) | `open_predictor/sources/market/alpaca.py` | new |
| Webull live NOII (#1) | `open_predictor/forecast/auction/vendors/stitch/webull.py` | new |
| Nasdaq ITCH sample fetcher (#1 hist) | `open_predictor/forecast/auction/vendors/itch/samples.py` | new (parser `open_predictor/forecast/auction/vendors/itch/parse.py` exists) |
| NYSE TAQ sample fetcher (#2 hist) | `open_predictor/forecast/auction/vendors/taq/samples.py` | new (parser `open_predictor/forecast/auction/vendors/taq/parse.py` exists) |
| Massive live NYSE imbalance (#2 live) | `open_predictor/forecast/auction/vendors/stitch/feeds.py` | stub to finish |
| Alpaca news stream (news wire) | `open_predictor/forecast/news/sources/alpaca.py` | new |
