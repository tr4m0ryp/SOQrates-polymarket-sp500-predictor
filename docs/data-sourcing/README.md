# Auction-data sourcing — knowledge base

Everything we established while sourcing the **Track-3 auction layer** (the opening-cross
microstructure that lets us predict the official SPX 9:30 open before the futures crowd).
Captured 2026-07-18; research **parked** here pending account/access decisions.

The quick-reference table lives at repo root in [`data_sources.md`](../../data_sources.md).
This directory is the detailed reasoning behind it.

## Files

| File | What's in it |
|---|---|
| [01-requirements.md](01-requirements.md) | The 4 data types we need, hist vs live, and the pipeline seams they feed |
| [02-vendors-evaluated.md](02-vendors-evaluated.md) | Every vendor/source assessed — coverage matrix + per-vendor verdict |
| [03-decided-stack.md](03-decided-stack.md) | The chosen sources per need, cost, and the adapters left to build |
| [04-verified-facts.md](04-verified-facts.md) | Adjudicated facts + refuted claims, with primary sources |
| [05-implementation-status.md](05-implementation-status.md) | What's built / wired / pending + day-1 activation checklists |
| [06-open-questions.md](06-open-questions.md) | Remaining gaps and the decisions still to make |

## State in one paragraph

The **historical / backtest** side is essentially solved and free via **WRDS** (NYSE Daily
TAQ: NYSE imbalance + cross prints + NBBO, arbitrary dates) — with **one gap**: Nasdaq NOII
history, which WRDS does not carry, so it needs **Databento** (client built, pending payment)
or self-recording forward. The **live / production** side is best served by a single **IBKR**
account (both venues via tick 225, EU-reachable, ~$17–40/mo). The **Databento** integration is
built and verified; **two adapters remain** — a WRDS fetcher and an IBKR live client.

## Decided stack (short)

- **Historical:** WRDS (NYSE imbalance, cross prints, NBBO) + Databento (Nasdaq NOII).
- **Live:** IBKR (all four legs, one account) — or free Webull(Nasdaq)+Massive($49) stitch.
- **Cost:** backtest ~$0 · live ~$17–40/mo.
- **Constraint:** WRDS is research-only — validates the model, cannot power live trading.
