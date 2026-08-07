# Handoff — conclusion

## Status

Written (outline block active; not MERGED/DROPPED). 354 prose words
(target 300–450). File: sections/conclusion.tex. No figures assigned; the
figures manifest was not touched. main.tex not edited.

## Exemplar support

Fetched once for this section:
`corpus.py exemplars --role conclusion --lang en --dtype paper -t "prediction market futures gap edge trading validation" -k 3`

- note: role 'conclusion' thin for en (2 match); backfilled 1 from role 'other'
- Exemplar 1/3 #7 [shinyhunter] conclusion/en w=1.0 solo=1 — primary anchor
  (recap opening, paired-verdict close, forward-pointing final paragraph).
- Exemplar 2/3 #63 [neurips-2026-formatting] conclusion/en w=0.7 solo=0 —
  secondary anchor (dense "we did X, we did Y" recap rhythm).
- Exemplar 3/3 #67 [avelero-espresso] other/en w=0.7 solo=0 — role backfill,
  off-topic (LCA methodology prose); not used as an anchor. Support is
  therefore effectively 2 on-role exemplars; the role is known-thin for en.

## Lint

- Band: en/paper, tolerance 1.5, invocation
  `check.py --lang en --dtype paper --tolerance 1.5 --json -` (stdin).
- Exit code: 1 (advisory only per calibrated policy).
- Misses: 1 of 8 → PASS under the calibrated policy (PASS = at most 2 of 8
  outside band); no revise round triggered (revise only when >2 miss).
- Per-metric:
  | metric | value | mean | sd | pass |
  |---|---|---|---|---|
  | sent_len_mean | 19.222 | 18.735 | 5.296 | yes |
  | sent_len_sd | 13.935 | 11.095 | 2.587 | yes |
  | para_words_mean | 86.500 | 77.491 | 33.333 | yes |
  | para_words_sd | 16.263 | 37.208 | 26.446 | yes |
  | signpost_per_1k | 0.000 | 0.115 | 0.365 | yes |
  | mtld | 108.123 | 121.519 | 29.846 | yes |
  | first_person_per_1k | 5.780 | 8.884 | 8.171 | yes |
  | readability | 70.733 | 37.204 | 6.711 | **no** |
- Honest note on the miss: readability (Flesch-type, higher = plainer) is
  well above the paper band, not a near-miss. The conclusion restates
  numbers in short declarative sentences with almost no subordinate
  clauses, which reads far "easier" than his method/discussion prose. The
  register spec ("short common words; one idea per sentence") pulls this
  metric up by construction in a 4-paragraph restatement section; the
  calibrated policy classifies it as a pass, so it was left standing rather
  than padded with longer words to game the score.

## Content decisions

- Claims restated: 11 (k=1, sigma=0 crowd error), 19 (k ≈ 0.77–0.80,
  a0 = 0.0092%), 21 (72.5% → ~94% ladder, 200 days), 70 per C1 ($135.92
  paired with bet_frac 0.10), 77 ($850.69 paired with the
  min(1/2 balance, $400, 1% volume) rule; ~$1k/day 1%-of-volume ceiling),
  86 (monthly re-validation mandatory), 87 (7-step rule compressed to one
  sentence), 62+100 (replica on real NOII/imbalance data; $0 validation,
  ~$17–40/mo live; quirk days 2-of-12 strictly called → majority, stated
  as the C6 strict metric).
- Citation: \parencite{polymarket2026spxmarket} only (outline marks it
  optional; key exists in references.bib). No other keys used.
- Must-say coverage: persistent k=1 mispricing; edge real but capped near
  $1k/day by market liquidity; conditional on monthly re-validation;
  replica on real auction data framed as the identified next step, not a
  promise of more accuracy from the same inputs ("The next step is not more
  accuracy from the same inputs").
- Paragraph shape: recap "We measured..." opening (shinyhunter conclusion
  pattern), distinct from the discussion's verdict-opener subsections; no
  new numbers, no figures, no lists.
