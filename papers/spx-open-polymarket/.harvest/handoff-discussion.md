# Handoff — discussion

## Status

Written to `sections/discussion.tex` (~1,809 body words excluding floats and
run-in heads; outline target 1,500–1,900). Seven blocks per the outline:
anatomy of the misses; the two test losses; quirk days and the crowd; the
ceiling and the replica path; competitive landscape ("Who else is in the
market"); negative results (dense prose, no list); limitations as eight
\paragraph-headed blocks (~450 words), each naming its fix and stopping.

## Content coverage vs outline block

- Miss anatomy: 27 (Jul 10 omitted from the quirk/massacre list per C7 —
  handled as a reclassified late-flip in the losses block), 28 (zero
  unexplained), 29 (March 2026 clustering + \textcite{ahoniemi2016overnight}),
  30 (24 of 27 last flips 8:30–9:30), 24 (94% future news; ±0.08–0.09%
  floor; perfect per-stock model adds 1–2 points).
- Two losses: 81 in full (Jul 2 news reversal with the $77-of-$296
  recoverable detail; Jul 10 late futures flip, $654 swing), per C7.
- Quirk days and the crowd: 8 (once-a-month cadence; the 94–99c/116-market
  evidence stayed in the Introduction, not repeated), 10 (Mar 10
  TradingView 6,792.83 vs official 6,796.56; Apr 9 = 41 comments; ETF leg
  breaking on the Jun 22 dividend date — details the intro did not use),
  25 (±6-pt floor; Jun 22 −0.14 vs +1.7..+5.7), 36 (per C6: "4 of 12 safe"
  defined as right-or-no-bet at 9:00 under v1.2; confidence softening),
  117 (futures cannot catch quirks at any hour).
- Ceiling → replica: 22, 56 (1.7/0.75 pts vs 6-pt floor, 3–8x), 57 (1s
  cadence + "best predictor" quote, \parencite{nasdaq2026totalview}), 62
  (per C6: "2 of 12 strictly called correctly on futures alone" framing;
  payoff flagged as projections, not backtest results), 64 (trades add
  nothing; quotes/auction data required), 65 (fusion open question stated,
  left unsolved).
- Competitive landscape: 97 (sniper, longshot harvester, futures
  confirmers, empty pre-print slot, Jun 30), 98 (insider scan negative;
  Taut-Morsel unnamed — "the best streak found, 12 of 12" — chance
  baseline ~6/242), 99 (Brier 0.059 vs 0.071, +20%/trade, 18 days), 84
  (hindsight $7,315 vs $164; Jun 1 = 82%; timing oracle $569; 31/58 days
  best price 00:00–2:00), 86 (1.45 vs 1.28 multipliers, fee arrival,
  monthly re-validation), 94 (maker posture, 5c modeled ≠ 5c capturable,
  \parencite{polymarket2026orders}).
- Negative results: 119, 120 (brief — the number 7 oc-misses stayed in
  Results), 121, 51 (calendar justification), 49 ($357/$359, $314/$322),
  50+124 (2/1/3 of 6, retrieval > model), 74 (2c vs 62c dips, all patient
  variants lose), 80 (midnight ruin despite 62% wins), 122 (families
  deferred to Table tab:strategy_graveyard by cross-reference; the
  sizing=optimal=all-in item kept), 118 covered in the replica block via
  64, 125 covered in the competitive block via 98. No item is stated
  twice with the same numbers.
- Limitations (each fix named): 88 split into three paragraphs (one
  regime/58 days + learning crowd; midpoint curves; shrinking market with
  C4 volume phrasing "$664k → $30–48k"), 41 (465d caution), 61 (replica
  synthetic-only), 95 (execution unknowns), 100+101+104 (research-only
  licenses; \parencite{wrds2026taq, lseg2026tickhistory,
  databento2026equities, nyse2026taqimbalances}; ~$17–40/mo live route),
  53+126 (BLS block, NFP-only calendar, 20/465 days flagged).
- Figures: `spx_open_predictor_misses` placed [h] after its introducing
  paragraph with edited manifest caption (Jul 10 recaptioned from "quirk
  day where futures held the opposite direction" to "late futures flip"
  per C7), label fig:spx_open_predictor_misses, one in-prose reference.
  Hero fig:spx_open_predictor re-referenced in the sigma-decomposition
  paragraph. Manifest status for the misses figure already read "placed"
  (set concurrently by another agent); required end state holds, no edit
  made.
- Citations used, all present in references.bib: ahoniemi2016overnight,
  stollwhaley1990, nasdaq2026totalview, polymarket2026orders, wrds2026taq,
  lseg2026tickhistory, databento2026equities, nyse2026taqimbalances.
  shannon1948 left uncited per the outline header; Liu & Tse not touched
  (method-section concern).

## Exemplar support

Command: `corpus.py exemplars --role discussion --lang en --dtype paper -t
"miss attribution auction quirk ceiling limitations negative results edge
persistence market" -k 3`

- `note:` lines printed by the command (verbatim):
  - note: role 'discussion' thin for en (2 match); backfilled 1 from role 'other'
- Returned 3/3: #6 [shinyhunter] discussion w=1.0 solo=1;
  #62 [neurips-2026-formatting] discussion w=0.7 solo=0;
  #67 [avelero-espresso] other w=0.7 solo=0 (backfill).
- #6 (shinyhunter) was the primary anchor: \paragraph-headed limitation
  blocks with blunt claim-first heads, caveats standing against the
  paper's own result, "X is not the same as Y" verdicts. The limitations
  block follows this anchor directly.
- #62 anchored the mechanism-then-consequence rhythm of the discussion
  paragraphs and the "names its fix, then stops" limitation shape.
- #67 (backfilled from 'other') is off-register methods prose and was not
  used as an anchor.
- Support is moderate: only 2 true discussion exemplars exist for en, but
  #6 is solo weight-1.0 and directly on-register for this section.

## Stylecheck

- Band: en/paper. Tolerance: 1.5. Final exit code: 1 (advisory only; the
  caller's calibrated policy is PASS = at most 2 of 8 metrics outside
  band via --json miss count).
- Rounds: initial lint = 4 misses (sent_len_sd 18.41, para_words_mean
  142.14, para_words_sd 130.42, readability 60.02) → revision round 1
  (split the longest sentences and oversized paragraphs; no content
  change) → 1 miss. Loop stopped (at or under the 2-miss threshold).
- Misses (final): 1 of 8 — PASS.

| metric | value | mean | sd | band @1.5 | pass |
|---|---|---|---|---|---|
| sent_len_mean | 17.964 | 18.735 | 5.296 | 10.79–26.68 | yes |
| sent_len_sd | 10.180 | 11.095 | 2.587 | 7.21–14.98 | yes |
| para_words_mean | 82.333 | 77.491 | 33.333 | 27.49–127.49 | yes |
| para_words_sd | 51.335 | 37.208 | 26.446 | 0–76.88 | yes |
| signpost_per_1k | 0.0 | 0.115 | 0.365 | 0–0.66 | yes |
| mtld | 104.500 | 121.519 | 29.846 | 76.75–166.29 | yes |
| first_person_per_1k | 8.097 | 8.884 | 8.171 | 0–21.14 | yes |
| readability | 64.978 | 37.204 | 6.711 | 27.14–47.27 | NO |

- The residual miss is readability, ~17.7 points above the upper band
  (reads easier/plainer than his measured paper band). Same direction as
  the introduction (50.5) and method (58.1) misses; number-dense short-word
  prose inflates Flesch ease, and the round-1 sentence splits raised it
  further (60.0 → 65.0) while fixing the three structural misses. Not
  chased with filler per the loop policy.

## Conflicts / profile-vs-template notes

- latex.md's paper register (natbib \citep/\citet) conflicts with the
  template's biblatex authoryear-comp; the template won — \parencite /
  \textcite used, consistent with the other sections.
- main.tex loads no amsmath/float: no \text in this section's math (the
  figure caption says "the model's probability of an up open" in words),
  inline math only, figure placed [h] (not [H]).
- C7 enforced against the manifest caption_draft: the draft called Jul 10
  "a quirk day where futures held the opposite direction"; the placed
  caption says "a late futures flip: the gap crossed zero only after
  9:00". C6 enforced twice (4/12 right-or-no-bet at 9:00; 2 of 12
  strictly called correctly, futures only) with the metric defined inline
  at each use.
- Claims 8/10 overlap with the Introduction; the discussion uses only the
  details the intro did not (Mar 10 TradingView numbers, Apr 9 comment
  count) and does not repeat the 94–99c/116-market or "lost 5k" evidence.
