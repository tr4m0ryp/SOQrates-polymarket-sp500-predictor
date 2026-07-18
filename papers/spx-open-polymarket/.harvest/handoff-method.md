# Handoff — method

## Status

Written to `sections/method.tex` (~1,420 body words; outline target
1,200–1,500). Six subsections per the outline block: data & ground truth;
core model; regime and news extensions; fusion; auction replica; strategy
laboratory. Procedure and parameters only; interpretation left for
Discussion. Four displayed equations (core+width, flip risk, fusion,
replica), each followed immediately by a Symbol/Meaning table, plus the
fitted-constants table (`tab:fitted_constants`, placed [h] after its
introducing paragraph, takeaway caption above the tabular).

## Content coverage vs outline block

- Data/ground truth: claims 12, 13 (per C5: Yahoo ^GSPC cross-checked vs
  stooq, WSJ-only note not resurrected), 14, 15, 16, 17, 18.
- Core model: 19 (eq:core + symbol table), 20 (width law + hourly sigma
  ladder), 26 (eq:flip + symbol table + the 1%/30% example).
- Versions/constants: 31 (background only: regime-sigma blend mechanism,
  no v1.1 tercile values quoted), 34 (phrased as "consistent with reported
  large-gap reversal effects" — NO citation key, per the outline header
  rule; Liu & Tse never named), 35 (v1.2 terciles 0.733/0.827/0.839 per
  C3, small-gap k, NFP sigma), 37 (v1.3 composition + production split
  h<5/h>=5; Brier numbers left for Results), 38 (1.29 release-morning
  multiplier, clamp (1.0, 2.5)), 42 (no-ML guardrail), 40 (fitted-constants
  table, method-table option chosen over appendix).
- Fusion: 39 (eq:fusion + symbol table; sigma floors, sharpest voice wins).
- News layer: 43, 45, 46, 47, 48 (per C8: 1.9 pooled post-shock, 1.32
  train-only lab refit, 1.29 NFP release-morning kept distinct — also
  stated in the table caption), 52, 53.
- Replica: 54 (eq:replica + symbol table), 59, 60, 63, 105 (free-sample
  provenance; parsers-not-days caveat; synthetic-only status stated).
- Strategy lab: 66, 67, 68, 69 (all four audit defects named), 87 (7-step
  spec as an enumerate — a true ordered procedure; 7 items slightly exceeds
  his ~6-item habit but the spec is harvested as exactly 7 steps), 96.
- Figures: none assigned (per outline); `figures/manifest.json` untouched.
- Citations used, all present in references.bib: yahoo2026chartapi,
  stooq2026spx, slickcharts2026sp500, nasdaqtrader2026listed,
  polymarket2026gamma, gdelt2017doc, fred2026releasedates,
  ahoniemi2016overnight, nasdaq2026totalview, nasdaq2026itchsamples,
  nyse2026taqimbalances, polymarket2026clob, polymarket2026orders.
  shannon1948 left uncited per the outline header.

## Exemplar support

Command: `corpus.py exemplars --role method --lang en --dtype paper -t
"futures gap model sigma fusion backtest execution auction replica
strategy" -k 3`

- Returned 3/3: #59 [neurips-2026-formatting], #69
  [research-carbon-footprint-model], #66 [avelero-espresso]. All w=0.7,
  solo=0 — no solo weight-1.0 method exemplar exists for en/paper; support
  is moderate in count but off-topic (all three are carbon-footprint /
  LCA methods; nothing finance-adjacent in the corpus).
- #59 (neurips-2026-formatting) was the primary register anchor:
  \paragraph-headed method moves, parameters stated inline with their
  fitting data, a negative-result block, dense-but-plain sentences. The
  \paragraph run-ins in the news subsection follow this anchor.
- #69 and #66 anchored equation-then-definition rhythm only; their
  heavier formal register (enumerated design principles, ISO boilerplate)
  was not reproduced.
- `note:` lines printed by the command: none.

## Stylecheck

- Band: en/paper. Tolerance: 1.5. Final exit code: 1 (advisory only per
  the caller's calibrated policy: PASS = at most 2 of 8 metrics outside
  band via --json miss count).
- Rounds used: 1 lint run, 0 revision rounds (misses never exceeded the
  2-metric threshold, so the revise loop was not entered).
- Misses (final): 1 of 8 — PASS.

| metric | value | mean | sd | band @1.5 | pass |
|---|---|---|---|---|---|
| sent_len_mean | 18.776 | 18.735 | 5.296 | 10.79–26.68 | yes |
| sent_len_sd | 12.295 | 11.095 | 2.587 | 7.21–14.98 | yes |
| para_words_mean | 47.567 | 77.491 | 33.333 | 27.49–127.49 | yes |
| para_words_sd | 37.712 | 37.208 | 26.446 | 0–76.88 | yes |
| signpost_per_1k | 0.0 | 0.115 | 0.365 | 0–0.66 | yes |
| mtld | 131.477 | 121.519 | 29.846 | 76.75–166.29 | yes |
| first_person_per_1k | 1.402 | 8.884 | 8.171 | 0–21.14 | yes |
| readability | 58.087 | 37.204 | 6.711 | 27.14–47.27 | NO |

- The single miss is readability, ~10.8 points above the upper band: the
  section reads plainer/easier than his measured paper band. Partly
  structural — the checker's LaTeX cleaning turns four symbol tables and
  a constants table into short plain fragments, which inflates the ease
  score for a parameter-dense section. Same direction as the
  introduction's sole miss (50.5). Not chased with filler per the loop
  policy (revise only above 2 misses).

## Conflicts / profile-vs-template notes

- latex.md's paper register (natbib \citep/\citet) conflicts with this
  template's biblatex authoryear-comp; the template won —
  \parencite/\textcite used, consistent with the introduction.
- main.tex loads no amsmath/amssymb/float: equations use plain-LaTeX
  \equation with \mathrm/\mbox (no \text/\tfrac/\operatorname), the
  replica indicator is \mathbf{1}[..] instead of an Iverson double
  bracket, and the constants table is placed [h] (not [H]).
- Claim 40's rounded terciles ("0.73/0.83/0.84") were replaced by the
  exact v1.2 values 0.733/0.827/0.839 in the table, per conflict rule C3.
