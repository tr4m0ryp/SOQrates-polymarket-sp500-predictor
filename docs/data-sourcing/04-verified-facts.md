# 04 · Verified facts & refuted claims

Adjudications made against primary sources or live tests during sourcing. AI-generated
suggestions were repeatedly wrong; these are what actually held up.

## Confirmed (with evidence)

**LSEG credentials.**
- **DSWS** accounts (`ZLOL001`, `ZLOL003`) authenticate (HTTP 200, token) — but DSWS is
  **Datastream** (macro time-series), **not** tick history. Wrong product for us.
- **DSS** accounts (`9023786` etc.) are **untestable from here** — `selectapi.datascope.
  refinitiv.com` resets the TLS handshake before auth (edge IP-allowlist). Not a password
  issue. Needs an approved network (campus/VPN).

**Massive (ex-Polygon).**
- Free Basic tier has **no websocket** — verified live: `auth_failed: "Your plan doesn't
  include websocket access."`
- The NOI imbalance feed is the **$49/mo Imbalances Expansion** add-on — **NYSE-only**, and
  **real-time only** (`Plan History: Not applicable`, no imbalance history at any tier).
- The free Basic **REST** key *does* return official per-stock daily opens (`/v1/open-close`,
  grouped-daily), 2yr history — a free source for #3 price (no timestamp).

**Webull.**
- NOII = **Nasdaq-listed only** ("NASDAQ names… NYSE's separate feed" excluded). Does **not**
  provide NYSE imbalance.
- The official **OpenAPI** has a documented `/market-data/stock/noii/snapshot` endpoint — the
  compliant way in (built as `spx/replica/vendors/stitch/webull.py`).
- Reverse-engineering the desktop client / copying tokens = **ToS + market-data-license
  violation** (retail Level 2 is display-only). Not built.

**Sierra Chart.** (support thread [#74965](https://www.sierrachart.com/SupportBoard.php?ThreadID=74965))
- **Has** live Nasdaq NOII since 2022 (Quote Board fields + ACSIL + a nonstandard DTC message).
- **No historical storage** — staff: *"real-time accessible only, not historical."*
- **Nasdaq only** — imbalance "not available for NYSE/AMEX." Windows-only; DTC/C++ extraction.

**IBKR.** `reqMktData` generic tick **225** → auction price + imbalance for the primary
listing (both venues). Live-only, no historical imbalance. EU-reachable.

**WRDS.** ([NYSE TAQ Order Imbalances](https://www.nyse.com/market-data/historical/taq-order-imbalances))
- TAQ imbalance = **NYSE Group only** (NYSE, NYSE Arca, NYSE American). *"NASDAQ-listed names
  will not appear."* **No Nasdaq NOII.**
- **Has** free historical NYSE imbalance + cross prints (ms ts + venue) + NBBO, arbitrary dates.
- Research-only license — no live/production trading.

**Databento.** Covers all four, both venues, hist+live, arbitrary dates. Historical =
stdlib HTTP+JSON; live = optional SDK. Card-blocked for us.

## Refuted claims (adversarially killed)

| Claim | Reality |
|---|---|
| Databento $125 free credits fund a NOII pull despite the card | **Refuted 0-3 / 0-2** — not a workaround |
| Sierra backfills historical NOII ("open a past date, it downloads") | **False** — Sierra stores no imbalance history |
| Sierra / Webull provides NYSE imbalance | **False** — both Nasdaq-only |
| WRDS TAQ contains Nasdaq NOII (`TAQ.IMBALANCE`) | **False** — NYSE-group only; table names betray it |
| Webull app shows NYSE imbalance | **False** — NOII is Nasdaq-listed only |
| Massive free tier can pull imbalance | **False** — no websocket on free tier |
| Aggregators (EODHD/Polygon/Theta/Alpha Vantage) carry NOII | **False** — none carry auction imbalance |
| Reverse-engineering a broker app for historical/live NOII | **Rejected** — ToS + license violation; data often not even there |

## Recurring failure mode

AI answers optimized for **"tick data"** and kept recommending aggregators, or asserted
imbalance coverage that vendor docs contradict. **Anchor searches on the exact terms**
("NOII", "net order imbalance", "opening auction imbalance") and verify against the vendor's
own docs / a live auth test before trusting any coverage claim.
