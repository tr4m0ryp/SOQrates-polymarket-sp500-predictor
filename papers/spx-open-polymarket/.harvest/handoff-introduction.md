# Handoff — introduction

## Status

Written to `sections/introduction.tex` (818 body words; outline target 700–900).
A prior draft of this section existed in the file (earlier incomplete run: no
handoff had been written). It was verified claim-by-claim against
`.harvest/context.md`, kept as the base, and finished under the full
style-engine protocol (exemplars fetched, register applied, linted, two
voice-fidelity micro-edits: E-mini glossed at first use; partitive
construction in P2 fixed).

## Content coverage vs outline block

- P1 context/mechanism: claims 1, 2, 3 (phrased per C4: "~$664k/day in
  January 2026 declining to ~$30–48k by July 2026"), 4, 5, 6, 7.
- P2 crowd error: claims 8, 9, 10, 11 (+ the ~80% pass-through from 19,
  required by the block's Must-say).
- P3 prior work, one dense paragraph: stollwhaley1990, ahoniemilanne2013,
  ahoniemi2016overnight, hansenlunde2005, patton2011ranking,
  spdji2026indexmath, cme2026soq; closes with the composition-novelty
  sentence.
- P4 approach + 5-item contributions itemize: claims 19, 20, 21, 66, 69,
  70 (per C1: $135.92 paired with bet_frac 0.10), 72/77 (per C2: $321.53
  flat $50; $850.69 under min(1/2 balance, $400, 1% volume)), 27, 28.
- P5 roadmap, IMRAD register, 1 sentence.
- Figures: none (per outline). `figures/manifest.json` untouched.
- All cited keys exist in `references.bib`; citation commands are
  \parencite/\textcite matching main.tex's biblatex authoryear-comp setup.

## Exemplar support

Command: `corpus.py exemplars --role intro --lang en --dtype paper -t
"prediction market S&P 500 official open futures gap crowd" -k 3`

- Returned 3/3: #65 [avelero-espresso], #68 [research-carbon-footprint-model],
  #55 [neurips-2026-formatting]. All w=0.7, solo=0 — no solo weight-1.0 intro
  exemplar exists for en/paper; support is moderate, not weak in count but
  off-topic (all three are carbon-footprint/ESPResso intros; nothing
  finance-adjacent in the corpus).
- #65 and #68 are near-duplicate texts of the same intro from two projects,
  so effective diversity is 2 projects, not 3.
- #55 (neurips-2026-formatting) was the primary register anchor: verdict
  openers, short declaratives, dense-fact paragraphs, contributions list.
- `note:` lines printed by the command: none.

## Stylecheck

- Band: en/paper. Tolerance: 1.5. Final exit code: 1 (advisory only per
  caller's calibrated lint policy: PASS = at most 2 of 8 metrics outside
  band via --json miss count).
- Rounds used: 2 lint runs, 0 metric-chasing revisions (misses never
  exceeded 2; the micro-edits between runs were voice edits, not lint
  chasing).
- Misses (final): 1 of 8 — PASS.

| metric | value | mean | sd | band @1.5 | pass |
|---|---|---|---|---|---|
| sent_len_mean | 23.75 | 18.735 | 5.296 | 10.79–26.68 | yes |
| sent_len_sd | 11.262 | 11.095 | 2.587 | 7.21–14.98 | yes |
| para_words_mean | 77.727 | 77.491 | 33.333 | 27.49–127.49 | yes |
| para_words_sd | 60.879 | 37.208 | 26.446 | 0–76.88 | yes |
| signpost_per_1k | 0.0 | 0.115 | 0.365 | 0–0.66 | yes |
| mtld | 107.605 | 121.519 | 29.846 | 76.75–166.29 | yes |
| first_person_per_1k | 4.678 | 8.884 | 8.171 | 0–21.14 | yes |
| readability | 50.462 | 37.204 | 6.711 | 27.14–47.27 | NO |

- The single miss is readability, ~3.2 points above the upper bound: the
  draft reads slightly plainer/easier than his measured paper band. Treated
  as calibration noise per stylecheck/calibration.md (1–2 metric near-miss);
  not chased with filler.

## Conflicts / profile-vs-template notes

- latex.md's paper register (natbib \citep/\citet, NeurIPS) conflicts with
  this template's biblatex authoryear-comp; the template won —
  \parencite/\textcite used, matching his coursework biblatex idiom.
- Liu & Tse and shannon1948 rules (outline header) do not touch this
  section; nothing cited without a bib key.
