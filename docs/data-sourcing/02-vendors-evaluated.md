# 02 · Vendors & sources evaluated

Coverage against the four data types (see [01](01-requirements.md)). `hist` = arbitrary-date
backfill; `live` = real-time; `fwd` = self-record forward only.

## Master matrix

| Source | #1 Nasdaq NOII | #2 NYSE imbalance | #3 prints | #4 NBBO | Mode | Cost | Region | Verdict |
|---|---|---|---|---|---|---|---|---|
| **Databento** | ✅ | ✅ | ✅ | ✅ | hist+live | metered ~$0–50 hist · ~$100–200/mo live | API | **Everything** — card-blocked |
| **WRDS (NYSE Daily TAQ)** | ❌ | ✅ | ✅ | ✅ | hist only | **Free** (academic) | — | **Best historical**, research-only |
| **IBKR** | ✅ | ✅ | ✅ | ✅ | live only | ~$17–40/mo | **EU ✅** | **Best live** — one account, both venues |
| dxFeed | ✅ | ✅ | ✅ | ✅ | hist+live | enterprise quote (on-demand hist) | API | True equal to Databento, pricier |
| Bloomberg | ✅ | ✅ | ✅ | ✅ | hist+live | five-figure/yr | terminal | Complete but normalized, overkill |
| LSEG Tick History (DSS) | ✅ | ✅ | ✅ | ✅ | hist (live separate) | $1k+/mo · academic free | IP-walled | Blocked: edge refuses our IP |
| BMLL | ✅ | ✅ | ✅ | ✅ | **hist only** | enterprise | API | Databento-grade history, no live |
| AlgoSeek | ✅ | ✅ | ✅ | ✅ | hist only | buy-the-days | API | Cheaper historical, per-day |
| Webull | ✅ (Nasdaq only) | ❌ | ~ | ~ | live only | **Free** (OpenAPI) | **uncertain** | Free Nasdaq-live leg; access risk |
| Massive (ex-Polygon) | ❌ | ✅ | ✅ (open-close) | ~ | live (#2) · hist (#3 free REST) | $49/mo NOI add-on | API | NYSE-only imbalance, no history |
| Sierra Chart | ✅ (Nasdaq only) | ❌ | ✅ | ✅ | **live only** (no NOII storage) | ~$27–46/mo + fees | Windows | Live Nasdaq NOII, no history, no NYSE |
| Sterling / DAS Pro | ✅ (visual) | ✅ (visual) | ~ | ~ | live, **no API** | $150–250/mo | — | Screen-only, not automatable |
| Moomoo / thinkorswim | ✅ (visual) | ~ | ~ | ~ | live, no imbalance API | free | — | Display-only |
| Nasdaq NCDS / Data Link | ✅ (Nasdaq only) | ❌ | — | — | live sub | flat sub, Nasdaq agreement | API | Server-side Nasdaq NOII, no NYSE |
| Free ITCH samples (emi.nasdaq.com) | ✅ | ❌ | ✅ | reconstruct | hist (fixed dates) | Free | — | Bootstrap; dates 2019/2022 only |
| Free NYSE TAQ samples (ftp.nyse.com) | ❌ | ✅ | — | — | hist (sample dates) | Free | — | A few published dates only |
| TradingPhysics | ✅ | ❌ | ✅ | — | hist per-file | cheap per-day | — | Buy exact quirk days (unverified) |
| LOBSTER | ❌ (skips NOII) | ❌ | ✅ | ✅ | hist only | free sample · £7,499/yr | — | No imbalance; reconstructs book |
| Polygon.io / Theta / EODHD / Alpha Vantage / Market Data App | ❌ | ❌ | ~ | ~ | — | flat/cheap | API | **Aggregators — no imbalance at all** |
| Alpaca | ❌ | ❌ | ✅ (auctions) | ~ (IEX) | hist+live | free · $99/mo SIP | uncertain | Prints + quotes only, no imbalance |

## Key per-vendor notes

**Databento** — the only usage-metered vendor that covers all four, both venues, hist+live,
arbitrary dates. Client built (`spx/replica/vendors/databento/`). Blocked only by card rejection; the
advertised $125 free credits were adversarially **refuted** — not a workaround.

**WRDS** — NYSE Daily TAQ gives NYSE imbalance + cross prints (ms ts + venue) + NBBO, free,
arbitrary dates back ~2003. **Does not carry Nasdaq NOII** (TAQ imbalance = NYSE-group only).
Research-only license — cannot power live trading.

**IBKR** — `reqMktData` generic tick **225** returns auction price + imbalance for the
primary-listing exchange, so one account covers **both** venues. Live-only, EU-reachable,
`ib_insync`. Coarser than raw NOII (no near/far/paired split); pro-fee classification risk;
needs IB Gateway running.

**Massive / Webull / Sierra** — each covers only *part*: Massive = NYSE live imbalance ($49/mo,
no history) + free REST open-close (#3); Webull = free Nasdaq NOII live (official OpenAPI),
Nasdaq-only, access uncertain; Sierra = live Nasdaq NOII via ACSIL/DTC but **no historical
storage** and no NYSE.

**Aggregators (Polygon, Theta Data, EODHD, Alpha Vantage, Market Data App)** — trades/quotes/
options only. **None carry auction imbalance** at any tier; repeatedly mis-suggested by AIs
that optimize for "tick data" instead of "NOII/imbalance".

See [04-verified-facts.md](04-verified-facts.md) for the primary-source adjudications.
