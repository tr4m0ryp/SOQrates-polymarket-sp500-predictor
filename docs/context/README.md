# Team Context Pack

This directory is the shared onboarding context for teammates opening this repo
in a fresh Claude Code session with no memory of the project. The eleven
numbered pages were written from the code itself, not from recollection: every
path, constant, and command in them was checked against the tree at writing
time. Read them instead of reverse-engineering `spx/` from scratch, and treat
them as part of the codebase: they are kept current with the code they
describe.

## Reading order

Pages 01, 02, and 09 are the minimum first read: what the project does, how
code executes, and how to run it. The rest are per-subsystem deep dives you can
read when you touch that area.

| Page | Title | Hook | First read |
|---|---|---|---|
| [01-project-overview.md](01-project-overview.md) | Project Overview | Predicts the official 9:30:00 ET S&P 500 opening print and trades it on Polymarket series 10945; the edge is that only ~80% of the overnight ES gap survives to the open. | yes |
| [02-architecture-dataflow.md](02-architecture-dataflow.md) | Architecture and Data Flow | `python3 .` -> `__main__.py` -> `spx/cli/__init__.py`; traces the four flows (prediction, auction replica, news, strategy sim) end to end. | yes |
| [03-data-and-macro.md](03-data-and-macro.md) | Data and Macro Layer | The stdlib-only fetchers in `spx/data/` and `spx/macro/`: Yahoo chart API, stooq cross-check, Slickcharts weights, FRED release calendar. | |
| [04-model.md](04-model.md) | The Prediction Model | How a futures gap becomes (mu, sigma) and P(up): the RegimeScaler, the four cores in `spx/model/core.py`, and every constant in `spx/config.py`. | |
| [05-replica.md](05-replica.md) | Stage 3: The Opening-Auction Replica | `spx/replica/` rebuilds the first index tick from per-stock auction indications; Databento primary, LSEG fallback, 2000-scenario Monte Carlo. | |
| [06-news.md](06-news.md) | The LLM News Layer | `spx/news/` reads overnight headlines through a provider-agnostic LLM runner and adds a fitted, bounded voice on conflicted days. | |
| [07-polymarket-and-strategy.md](07-polymarket-and-strategy.md) | Polymarket and the Strategy Lab | `spx/pm/` prices the live edge; `spx/strategy/` simulates betting rules against archived minute curves, which are midpoints, not trades. | |
| [08-backtest-and-evaluation.md](08-backtest-and-evaluation.md) | Backtesting and Evaluation | The 480-day dataset, chronological train/test halves, the quirk-day safety table, and White's reality check in `spx/backtest/`. | |
| [09-commands.md](09-commands.md) | CLI Commands | All 24 subcommands with prerequisites and ordering dependencies, such as `stage3` needing a prior `databento-pull`. | yes |
| [10-research-artifacts.md](10-research-artifacts.md) | Research Artifacts | Where figures, the NeurIPS-format paper, and the methodology drafts live, and the Overleaf sync rule (slug `soqrates`). | |
| [11-conventions-and-environment.md](11-conventions-and-environment.md) | Conventions and Environment | House rules, the full `.cache/` file map, and every environment key with the module that reads it. | |

## Quick start

```
git clone https://github.com/tr4m0ryp/sOQrates spx-open-predictor && cd spx-open-predictor   # Python 3.12+, stdlib only, nothing to install
python3 . backtest --rebuild   # builds .cache/dataset.json, prints train/test metrics
python3 . predict              # live P(up) now plus the Polymarket edge
# Derived data lands in .cache/ at the repo root (gitignored); delete a file to force a rebuild.
# Env keys (FRED_API_KEY, DATABENTO_API_KEY, LLM_*, ...) are plain shell environment variables, all optional; the table is in 11-conventions-and-environment.md.
```

## Keeping this pack honest

Whoever changes the architecture, a CLI command, or a data flow updates the
matching page here in the same commit. A stale context page is worse than none:
the next session will trust it. If a change makes a page's numbers wrong and
there is no time to rewrite the prose, at minimum correct the numbers and note
what moved.
