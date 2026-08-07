# Handoff — abstract (style-engine run, 2026-07-18)

## Status
Written. 185 words of abstract prose (target 140–200) in
sections/abstract.tex; hero figure `spx_open_predictor` placed as a [b]
float in the same file (bottom of page 1, shinyhunter hero pattern),
label `fig:spx_open_predictor`, status set to "placed" in
figures/manifest.json.

## Claims used
1, 11, 19, 21, 23, 70, 72, 88 — numbers exactly as harvested. C1/C2
honored: $321.53 paired with "flat $50 stakes" (first_signal, 26W–2L);
$135.92 paired with "10% of bankroll per trade" (hour-4 hold). k range
0.77–0.80, ladder 72.5% -> ~94%, coin-toss filter 65% -> 82.1%, caveats
from claim 88 (one regime, 58 test days, thinning market, learning crowd).
No citations (his abstracts don't cite).

## Figure delegation
The outline assigns the hero's FIRST in-prose reference to Results
("introduced by the first Results reference") and the re-reference to
Discussion; the abstract itself references no figures. The figure
environment, caption (edited from manifest caption_draft), and label are
placed here; the Results agent must supply Figure~\ref{fig:spx_open_predictor}
in prose. Compile agent: if the [b] float drifts off page 1, move the
figure environment to main.tex directly after \end{abstract}; keep the label.

## Exemplar support
Command: corpus.py exemplars --role abstract --lang en --dtype paper
-t "prediction market S&P 500 official open futures gap backtest" -k 3

CLI note line, verbatim:
note: role 'abstract' has no match for en; falling back to role 'other' (3 exemplar(s))

(A second literal "note:" string appears inside exemplar 2's own TEXT
block — corpus content, not a CLI fallback line.)

Anchors returned: shinyhunter (w=1.0, solo), avelero-espresso (w=0.7,
non-solo), neurips-2026-formatting (w=0.7, non-solo). Support is WEAK for
this role: no true abstract exemplar exists in the en corpus; rhythm was
anchored on shinyhunter's dense-claim + short-verdict pattern instead.

## Stylecheck
Command: check.py --lang en --dtype paper --tolerance 1.5 --json -
Band: en/paper. Tolerance: 1.5. Exit code: 1 (advisory only per lint
policy). Misses: 2 of 8 -> PASS under the calibrated policy (at most 2
allowed). No revision rounds used (0 of 3): policy revises only above 2
misses.

Per-metric misses:
- para_words_mean: value 169.0 vs band 77.49 +/- 1.5*33.33 (27.5–127.5).
  Structural: an abstract is one continuous paragraph; splitting it to
  chase the band would break the form.
- readability: value 67.28 vs band 37.20 +/- 1.5*6.71 (27.1–47.3).
  Flesch reads HIGH (simpler) because abstract sentences are short and
  plain; his paper band is measured over body prose.

Passing: sent_len_mean 18.78, sent_len_sd 9.00, para_words_sd 0.0,
signpost_per_1k 0.0, mtld 106.85, first_person_per_1k 5.92.

## Conflicts / profile notes
None between profile and template. main.tex wraps this file in
\begin{abstract}...\end{abstract}; the figure environment is emitted from
inside it deliberately so the float lands on page 1.
