# Handoff — results

Drafted by the style-engine protocol into `sections/results.tex`. Status: written.

## Exemplar support

Fetched once for this section:
`corpus.py exemplars --role results --lang en --dtype paper -t "accuracy backtest strategy calibration bankroll" -k 3`

note: role 'results' thin for en (1 match); backfilled 2 from role 'other'

- #60 [neurips-2026-formatting] results/en w=0.7 — the only true results-role hit; anchored the \paragraph-headed block structure, delta-reading paragraphs after floats, and the "are these errors small?" comparative register.
- #3 [shinyhunter] other/en w=1.0 solo=1 — methods-register anchor for dense enumerated procedure and caveat-in-caption idiom; used for rhythm only.
- #67 [avelero-espresso] other/en w=0.7 — off-register (working-note sprawl, contains raw scaffolding); disregarded as a rhythm anchor.

Support is moderate: only one genuine results exemplar (declared weak per the skill's failure-honesty rule); structure.md's measured results pattern (thin prose around floats, shinyhunter results = 250 w around 4 floats) was used as the primary structural anchor instead.

## Lint

- Band: en/paper (verdict band as requested; `--dtype paper`). Tolerance: 1.5.
- Final exit code: 1 (advisory only per caller's calibrated policy).
- Misses: 2 of 8 → PASS under the calibrated rule (at most 2 of 8 outside band).
- Revise rounds used: 2 of 3 (round 1 draft, round 2 trim+fuse). Misses were stable across rounds and pull in opposite directions (breaking sentences lowers sent_len_sd but raises readability ease; fusing does the reverse), a known artifact of number-dense results prose; loop stopped rather than gamed.

Per-metric misses (final):

| metric       | value  | mean   | sd    | band (±1.5 sd)   |
|--------------|--------|--------|-------|------------------|
| sent_len_sd  | 19.838 | 11.095 | 2.587 | 7.21 – 14.98     |
| readability  | 68.387 | 37.204 | 6.711 | 27.14 – 47.27    |

Passing: sent_len_mean 26.18, para_words_mean 108.0, para_words_sd 66.6, signpost_per_1k 0.0, mtld 101.5, first_person_per_1k 0.0.

## Content notes

- Word count: ~1,070 prose words (floats/captions excluded, rough detex count) against the outline's 550–800 target. Overshoot declared: the block carries 26 assigned claims plus all conflict-rule phrasings; two trim passes brought it down from ~1,140 and further cuts would drop assigned claim content.
- Floats: 3 tables (tab:accuracy_ladder, tab:calibration, tab:strategy_graveyard) + 5 figures placed in outline order; hero fig:spx_open_predictor received its formal in-prose reference (placed in abstract.tex, not re-placed here).
- Conflict rules honored: C1/C2 every bankroll paired with its sizing rule ($135.92 = 10% of bankroll; $264.30 = flat $50 hold-h4; $321.53 = first-signal flat $50; $850.69 = min(1/2 balance, $400, 1% volume)); C6 quirk metric stated ("right or no-bet at 9:00" for 4/12); C7 Jul 10 captioned as late futures flip; C8 release-morning 1.29 kept distinct from the shock multipliers.
- Caption edits vs manifest drafts: strategy_bankroll_50 caption corrected per C7 (manifest said "Jul 10 (quirk day)") and the manifest's "0.1% impact per $100" was dropped (conflicts with the harvested calibration of ~0.05 cents per $100); other captions tightened from their caption_draft text.
- Citations: none used (per outline: results cite own measurements; polymarket2026spxmarket not needed in any caption).
- Profile vs template conflicts: latex.md prefers [h]/[H] after the introducing paragraph; main.tex loads no float package, so [h] used throughout (template side won on [H]). Calibration table uses dashes for values not recorded in the harvest rather than inventing cells.
- Manifest: spx_open_predictor_0000_200d, spx_open_predictor_0400_200d, spx_open_predictor_0000_confident, strategy_bankroll_50, stake_sweep set to "placed".
