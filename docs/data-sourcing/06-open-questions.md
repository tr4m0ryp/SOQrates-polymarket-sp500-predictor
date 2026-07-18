# 06 · Open questions & pending decisions

What's unresolved, roughly in priority order. Research is **parked** here.

## 1. Nasdaq NOII historical — the one real gap

The highest-signal leg (~57% of index weight) has **no free arbitrary-date source**:
- WRDS **doesn't** carry it (TAQ imbalance = NYSE-group only).
- Free ITCH samples are date-limited (2019/2022) — won't cover our 2026 quirk days.
- **Options:** (a) **Databento** filtered pull (cheap, once payment clears); (b) **TradingPhysics**
  per-file for exact dates (unverified, ~few $/day); (c) **self-record forward** — start logging
  live Nasdaq NOII (IBKR/Webull) from today, build the archive going forward.
- **Decision needed:** pay for past-date backfill, or accept forward-only recording and wait
  for future quirk days.

## 2. Broker region access

The free/cheap live legs assume US-brokerage accounts:
- **IBKR** — opens to NL/EU residents → the safe live bet. ✅ (assumed, confirm on signup)
- **Webull / Moomoo** — US-oriented; access from NL **uncertain**. If they don't open, the
  free Nasdaq-live leg is gone and IBKR is the only live path.
- **Decision needed:** confirm IBKR account + which market-data subscriptions (and whether use
  classifies as **professional**, which multiplies data fees).

## 3. Databento payment

Card was rejected. Everything is built and waiting. **Decision:** resolve payment (alt card /
method), or commit to the WRDS(hist)+IBKR(live) path and treat Databento as optional.

## 4. Live NYSE imbalance cost

The only leg with no free option. **IBKR** folds it in for ~$17–40/mo (recommended); **Massive**
is $49/mo NYSE-only. Deferred until the live decision.

## 5. WRDS Nasdaq check (quick)

Standard WRDS TAQ has no Nasdaq NOII, but dataset menus vary by institution — **check the UvA
WRDS dataset list** for any standalone *Nasdaq TotalView / ITCH* product. If present, gap #1
closes for free.

## 6. Self-record-forward strategy

Since live NOII is cheap/free, a legitimate archive-builder is: log both venues' imbalance every
morning from today, compliantly, under the live entitlement. Complements past-date backfill.
**Decision:** stand up the recorder now (needs the IBKR client first), or wait.

## Next build (when unparked)

Recommended order:
1. **WRDS fetcher** — free, no pending dependency, unlocks the backtest immediately.
2. **IBKR live client** — the production live leg (also enables self-record-forward).
3. Databento — already built; activate when payment clears.
