# Research Artifacts and Where Writing Goes

Research output lives in two trees. `research/` holds the figures, the figure
manifest, and the paper. `docs/` holds the prose that is not the paper: the
methodology working draft and the data-sourcing knowledge base. This page maps
both and explains the Overleaf mirroring rule for the paper.

## Figures: `docs/research/plots/` and the manifest

`docs/research/plots/` contains nine PNGs: `spx_open_predictor.png`,
`spx_open_predictor_0000_200d.png`, `spx_open_predictor_0000_confident.png`,
`spx_open_predictor_0400_200d.png`, `spx_open_predictor_misses.png`,
`stake_sweep.png`, `strategy_bankroll_50.png`, `strategy_bankroll_50_band.png`,
and `reliability_diagram.png`. The same nine files are copied into
`docs/research/paper/figures/`, which is what `main.tex`
actually includes.

`docs/research/figures/manifest.json` is the ledger for these figures. It is a JSON
array with one object per figure, fields: `id`, `file` (repo-relative path
into `docs/research/plots/`), `status`, `caption_draft`, `producing_script`, plus
`data_source` and `notes`. Nine entries exist: eight `placed` (in the paper)
and one `waived` (`strategy_bankroll_50`, superseded by the band version).

The `producing_script` field is the honest part. Six figures have
`producing_script: null`: their generating scripts were session scratch and
were not retained, so they cannot be regenerated and the captions were written
from the images plus project memory. Three are regenerable:

- `reliability_diagram`: `open_predictor/evaluation/backtest/plot.py`, run
  `python3 -c 'from open_predictor.evaluation.backtest.plot import reliability_diagram; reliability_diagram()'`
  from the repo root.
- `strategy_bankroll_50_band`: `open_predictor/trading/strategy/analysis/plot.py` (`bankroll_band`),
  bands from `open_predictor/trading/strategy/analysis/bootstrap.py`, cached in
  `.cache/bootstrap_bands.json` (10,000 resamples, seed 20260719).
- `strategy_bankroll_50`: `open_predictor/trading/strategy/analysis/plot.py` (waived).

Manifest notes mention regenerated PDF versions alongside the PNGs, but no
`.pdf` files exist anywhere under `research/` today. Only the PNGs survive.

New figures follow the same contract: put the PNG in `docs/research/plots/`, add a
manifest entry with a caption draft and the producing script, and copy the file
into the paper's `figures/` directory if it is placed.

## The paper: `docs/research/paper/`

The paper is "SOQrates: Predicting the S&P 500 Opening Price", a NeurIPS 2026
preprint build (`neurips_2026.sty`, `[preprint]` option, numbered citations).
`main.tex` is a thin skeleton: abstract, a non-floating title-page teaser
figure, then Introduction, Methods, Results, Discussion, Conclusion, two
unnumbered back-matter sections (Broader Impacts, Data and Code Availability),
references from `references.bib`, six appendices, and `checklist.tex`. All body
text lives in `sections/`: `abstract.tex`, `introduction.tex`, `method.tex`,
`results.tex`, `discussion.tex`, `conclusion.tex`, `broader_impacts.tex`,
`availability.tex`, and `sections/appendix/` with `replica.tex`,
`execution.tex`, `news.tex`, `selection.tex`, `market.tex`, `trajectories.tex`.
Compile with pdflatex + bibtex as the comment at the top of `main.tex` states.

`.harvest/` is the paper-scribe state and is worth reading before touching any
section. `.harvest/context.md` is the master evidence file: 131 numbered claims
with provenance tags (repo, memory, transcript) plus 8 documented conflicts
(C1 to C8) that resolve which of two competing numbers the paper must cite,
for example that every bankroll figure must be paired with its sizing rule.
`.harvest/outline.md` records the structural decisions (IMRAD, no separate
related-work section, Discussion largest) and restates the conflict rules.
The other files are per-section handoffs (`handoff-*.md`), findings notes, and
rendered page images in `pages/` and `pages-edit/` used for visual QA.

## The Overleaf rule

The paper mirrors the Overleaf project with slug `soqrates` (recorded in
`~/projects/research/overleaf-mirror/manifest.tsv`). The rule from the
user-level CLAUDE.md: a paper that exists only on disk is not delivered.
Any material edit to the paper must be pushed to Overleaf in the same turn:

```bash
python3 ~/projects/research/style-corpus/overleaf/sync.py \
  --paper-dir docs/research/paper --name soqrates \
  --message "<what changed>"
```

Never mint a new slug for this paper. A new slug silently forks it into a
second Overleaf project that then drifts apart from the first. Updates need
only the git token; only creating a brand-new project needs a live browser
session, so an exit code 2 on an update-only push means the Chrome login
lapsed, not that the paper failed. The repo stays the source of truth;
Overleaf compiles its own PDF, so build output is never synced.

## `docs/`: the non-paper writing

`docs/research/approach.tex` (717 lines, working draft dated July 15, 2026) is the
plain-language methodology writeup that predates the paper: the bet and the
resolution number, the core market model, Layer R (auction replica), the news
layer, the fusion rule, the execution-realistic strategy backtest, current
status, open questions, a fitted-constants appendix, and a "Reproducing every
number" section mapping each number to a repo command. The paper superseded it
as the polished deliverable, but it remains the fullest single explanation and
the harvest cites it heavily.

`docs/build/data-vendors/` is the auction-data sourcing knowledge base, captured
2026-07-18 and explicitly parked pending account decisions. `README.md` is the
entry point and one-paragraph state summary; the numbered files are:

- `00-quick-reference.md`: coverage, cost, and status table per source.
- `01-requirements.md`: the 4 data types needed, historical vs live.
- `02-vendors-evaluated.md`: coverage matrix and per-vendor verdicts.
- `03-decided-stack.md`: chosen sources (WRDS + Databento historical, IBKR
  live, backtest ~$0, live ~$17 to $40/mo) and adapters left to build.
- `04-verified-facts.md`: adjudicated facts and refuted claims with sources.
- `05-implementation-status.md`: built vs pending, day-1 activation checklists.
- `06-open-questions.md`: remaining gaps.

`docs/build/system-guide/` is this set of team onboarding pages.

## Where to look

- `docs/research/figures/manifest.json`: which figures exist, which regenerate, and
  the caption drafts.
- `docs/research/paper/main.tex`: paper skeleton and build
  instructions.
- `docs/research/paper/.harvest/context.md`: 131 claims with
  provenance and the 8 conflict rulings; read before editing any section.
- `docs/research/approach.tex`: fullest prose explanation of model, replica, news, and
  strategy, with the reproduce-every-number section.
- `docs/build/data-vendors/README.md`: entry point to the auction-data sourcing
  decisions.
