# Data sources — coverage, cost, and implementation status

Reference for the SPX official-open predictor. Rows above the divider are the core
model (running today); the **bold** rows are the auction layer (Track 3), the reason
we went looking at LSEG. Sources for the auction layer were selected by the
2026-07-17 deep-research run (104 agents, 22 sources, 20 verified claims).

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
| **NYSE opening imbalance — historical** | **Yes — WRDS** | **WRDS NYSE Daily TAQ · Order-Imbalance file** (arbitrary dates, ~2003+, ms) | **Free** |
| **NYSE opening imbalance — live** | No | IBKR tick 225 / Massive NOI WebSocket | ~$40/mo · or $49/mo |
| **Per-stock opening cross print + ts** | **Yes — WRDS (hist)** | **WRDS TAQ trades** (price + ms ts + venue); IBKR/Alpaca live | **Free** |
| **Constituent quote midpoints (pre-open NBBO)** | **Yes — WRDS (hist)** | **WRDS TAQ NBBO** (ms consolidated); IBKR L1 / free IEX live | **Free** |

## Cost to operate

- **Validation / backtest:** **$0** — WRDS (NYSE Daily TAQ) covers NYSE imbalance + cross-prints
  + NBBO free for arbitrary dates; only Nasdaq NOII history needs free ITCH samples / Databento.
- **Go live:** **~$17–40/mo (IBKR)** — tick 225 gives both venues live, EU-reachable; or the
  free-ish Webull(Nasdaq)+Massive($49) stitch. WRDS is research-only and cannot power live trading.

## WRDS (access confirmed)

- **NYSE Daily TAQ** → Order-Imbalance file (#2 NYSE imbalance, arbitrary dates, ~2003+, ms),
  trades (#3 cross prints w/ exact ts + venue), NBBO (#4 quotes). Free, all constituents.
- **Caveats:** historical + **research-only** (academic license, no live, no production trading);
  **Nasdaq NOII is NOT in WRDS TAQ** (TAQ imbalance = NYSE-group only) — check the institution's
  dataset list for any Nasdaq TotalView/ITCH product, else samples/Databento/self-record.
- **TODO:** wire a small WRDS fetcher (WRDS Python/Postgres API) → feed stage3/timing like the
  Databento adapter does.

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
| Alpaca auctions (#3) + quotes (#4) | `data/alpaca.py` | new |
| Webull live NOII (#1) | `replica/webull_noii.py` | new |
| Nasdaq ITCH sample fetcher (#1 hist) | `replica/itch_samples.py` | new (parser `itch.py` exists) |
| NYSE TAQ sample fetcher (#2 hist) | `replica/nyse_taq_samples.py` | new (parser `nyse_taq.py` exists) |
| Massive live NYSE imbalance (#2 live) | `replica/feeds.py` | stub to finish |
| Alpaca news stream (news wire) | `news/alpaca_stream.py` | new |
