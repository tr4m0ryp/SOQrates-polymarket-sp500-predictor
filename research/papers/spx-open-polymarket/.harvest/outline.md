# Outline — SPX Official-Open Predictor vs the Polymarket Crowd

Skeleton per structure.md: IMRAD full paper (free-standing Conclusion is allowed
only in full papers — this is one, so it stays). No separate related-work
section: prior work is ONE dense paragraph inside the Introduction. Discussion
is the largest section (real findings exist). Results prose stays thin; tables,
figures and their read-the-delta paragraphs carry the numbers. Limitations are
NOT a separate section here: they live inside Discussion as \paragraph-headed
blocks (scheduling pattern; the fixed six-block plan has no Limitations slot).
Every displayed equation gets an immediate Symbol/Meaning table (his math
idiom). Every float is referenced by number and placed [h]/[H] after the
paragraph introducing it; table captions are 1–3 sentences stating the
takeaway, not the topic.

Body target ~4.8k–6.2k words (shinyhunter-scale substance; proportions follow
his measured pattern: Method+Results ~45%, Discussion largest).

Conflict rules the draft must honor (from context.md Conflicts):
- C1/C2: every bankroll number is paired with its sizing rule ($135.92 =
  bet_frac 0.10; $264.30 = flat $50; $321.53 = first_signal flat $50;
  $850.69 = first_signal under min(1/2 balance, $400, 1% volume)).
- C3: cite v1.2 tercile-k values 0.733/0.827/0.839, not v1.1's.
- C4: volume phrased as "~$664k/day in January 2026 declining to ~$30–48k by
  July 2026".
- C5: ground truth = Yahoo ^GSPC cross-checked vs stooq (the resolved, later
  finding); do not resurrect the WSJ-only note.
- C6: state the metric when citing quirk handling (4/12 = right-or-no-bet at
  h9 under v1.2; 2/12 = strictly called correctly, replica table framing).
- C7: Jul 10 = late futures flip (recoverable with the 9:28 leg); Jun 1 and
  Jun 22 are the true futures-invisible quirks.
- C8: keep the three multipliers distinct — pooled post-shock 1.9, strategy-lab
  train-only refit 1.32, NFP release-morning 1.29/1.3.
- Liu & Tse (claim 34) has NO bib entry: either add one in the draft phase or
  phrase as "consistent with reported large-gap reversal effects" without a key.
- shannon1948 has no natural home; leave uncited rather than ornament.

---

## abstract

- Target: 140–200 words.
- Claims: 1 [repo:CLAUDE.md] [conversation]; 11 [memory:spx-open-predictor-roadmap.md] [repo:docs/approach.tex];
  19 [memory:spx-open-predictor-roadmap.md] [repo:config.py] [repo:docs/approach.tex];
  21 [memory:spx-open-predictor-roadmap.md] [transcript:618d0dce];
  23 [memory:spx-open-predictor-roadmap.md] [repo:config.py] [transcript:618d0dce];
  70 [memory:polymarket-execution-microstructure.md] [transcript:380c3a0d];
  72 [memory:polymarket-execution-microstructure.md] [transcript:380c3a0d];
  88 [repo:docs/approach.tex].
- Figures: none inside the abstract; hero figure `spx_open_predictor` placed
  directly UNDER the abstract on page 1 (shinyhunter hero pattern), introduced
  by the first Results reference and re-referenced in Discussion.
- Citations: none (his abstracts don't cite).
- Must say: the Polymarket crowd prices the official S&P 500 open as if the
  futures gap realizes fully (k=1, sigma=0); measured, only ~80% realizes
  (k≈0.77–0.80), and a frozen linear model exploiting that gap achieves an
  out-of-sample accuracy ladder of 72.5%→~94% (midnight→9:29) over 200 days
  and survives a fee- and execution-audited backtest at 26W–2L — with the
  honest caveats attached (one regime, 58 test days).

## introduction

- Target: 700–900 words. 4–5 paragraphs + a contributions itemize (≤5 items)
  + a 1–2 sentence roadmap paragraph closing the section.
- Paragraph plan:
  - P1 context/definition — the market and the official-open mechanism:
    claims 1 [repo:CLAUDE.md] [conversation]; 2 [memory:spx-open-predictor-roadmap.md];
    3 [memory:spx-open-predictor-roadmap.md] (phrase per C4);
    4 [memory:spx-open-predictor-roadmap.md] [transcript:618d0dce];
    5 [memory:spx-open-predictor-roadmap.md] [repo:docs/approach.tex];
    6 [repo:docs/approach.tex]; 7 [memory:spx-open-predictor-roadmap.md] [transcript:618d0dce].
  - P2 the problem/tension — the crowd's error and what it costs:
    claims 8 [memory:spx-open-predictor-roadmap.md] [repo:docs/approach.tex];
    9 [repo:config.py]; 10 [transcript:618d0dce];
    11 [memory:spx-open-predictor-roadmap.md] [repo:docs/approach.tex].
  - P3 prior work, ONE dense paragraph (no related-work section):
    stale index opens vs futures (stollwhaley1990), overnight-return risk and
    regime spillover (ahoniemilanne2013, ahoniemi2016overnight), realized
    variance measurement (hansenlunde2005, patton2011ranking), index
    methodology and SOQ distinction (spdji2026indexmath, cme2026soq).
    Close with the shinyhunter-style novelty sentence: the novelty is not any
    single component but their composition and market-specific validation.
  - P4 approach + contributions itemize (4–5 items): frozen linear core with
    time-decaying sigma (19, 20 [memory:spx-open-predictor-roadmap.md]); the
    200-day OOS accuracy ladder (21); the audited strategy laboratory
    (66, 69 [repo:docs/approach.tex] [transcript:380c3a0d]); the validated
    trading rule (70, 72); the complete miss attribution + negative-results
    catalogue (27, 28 [memory:spx-open-predictor-roadmap.md]).
  - P5 roadmap, 1–2 sentences ("The remainder of the paper follows the IMRAD
    structure" register).
- Figures: none.
- Citations available: stollwhaley1990, ahoniemilanne2013, ahoniemi2016overnight,
  hansenlunde2005, patton2011ranking, spdji2026indexmath, cme2026soq,
  polymarket2026spxmarket, polymarket2026clob.
- Must say: the official open is a mechanical first-tick calculation in which
  only ~80% of the overnight futures gap realizes, while the crowd bets as if
  100% does — that 20% spread, plus its predictable noise structure, is the
  entire edge this paper measures and trades.

## method

- Target: 1,200–1,500 words. Procedure and parameters ONLY — interpretation
  waits for Discussion. Subsections: data & ground truth; core model; regime
  and news extensions; fusion; auction replica; strategy laboratory.
- Claims:
  - Data/ground truth: 12 [repo:CLAUDE.md] [conversation]; 13 [memory:spx-open-predictor-roadmap.md] (per C5);
    14 [repo:CLAUDE.md]; 15 [repo:CLAUDE.md] [conversation]; 16 [repo:data_sources.md] [repo:CLAUDE.md];
    17 [repo:config.py] [memory:spx-open-predictor-roadmap.md]; 18 [repo:CLAUDE.md].
  - Core model (displayed equation + Symbol/Meaning table): 19 [memory:spx-open-predictor-roadmap.md] [repo:config.py] [repo:docs/approach.tex];
    20 [memory:spx-open-predictor-roadmap.md]; 26 [transcript:618d0dce] (flip-risk
    formula, second equation + symbol table).
  - Versions/constants: 31 [memory:spx-open-predictor-roadmap.md] (background only — per C3 the
    quoted terciles are v1.2's); 34 [memory:spx-open-predictor-roadmap.md] [repo:config.py]
    (Liu & Tse — no bib key, see header rule); 35 [memory:spx-open-predictor-roadmap.md];
    37 [memory:spx-open-predictor-roadmap.md]; 38 [memory:spx-open-predictor-roadmap.md] [repo:config.py] (per C8);
    42 [repo:docs/approach.tex] (no-ML guardrail); 40 [repo:docs/approach.tex]
    (fitted-constants table — candidate appendix or method table).
  - Fusion (equation + symbol table): 39 [repo:model/fusion.py] [repo:docs/approach.tex].
  - News layer: 43 [memory:spx-open-predictor-roadmap.md] [repo:docs/approach.tex];
    45 [memory:spx-open-predictor-roadmap.md]; 46 [memory:spx-open-predictor-roadmap.md] [repo:docs/approach.tex];
    47 [memory:spx-open-predictor-roadmap.md] [repo:docs/approach.tex]; 48 [memory:polymarket-execution-microstructure.md] (per C8);
    52 [memory:spx-open-predictor-roadmap.md]; 53 [memory:spx-open-predictor-roadmap.md].
  - Replica machinery (equation + symbol table; synthetic-validated only):
    54 [repo:docs/approach.tex] [memory:spx-open-predictor-roadmap.md];
    59 [memory:spx-open-predictor-roadmap.md]; 60 [memory:spx-open-predictor-roadmap.md];
    63 [memory:spx-open-predictor-roadmap.md] [transcript:618d0dce];
    105 [memory:spx-open-predictor-roadmap.md] [repo:data_sources.md] [transcript:195168b9] (free sample provenance).
  - Strategy lab: 66 [memory:polymarket-execution-microstructure.md] [repo:docs/approach.tex];
    67 [memory:polymarket-execution-microstructure.md] [repo:docs/approach.tex] [transcript:380c3a0d];
    68 [repo:docs/approach.tex] [transcript:380c3a0d];
    69 [repo:docs/approach.tex] [transcript:380c3a0d] (the four audit defects — mandatory);
    87 [repo:docs/approach.tex] (7-step strategy spec, as procedure);
    96 [repo:pm/edge.py].
- Figures: none (method holds equations and parameter tables, not plots).
- Citations available: yahoo2026chartapi, stooq2026spx, slickcharts2026sp500,
  nasdaqtrader2026listed, fred2026releasedates, gdelt2017doc,
  polymarket2026clob, polymarket2026gamma, polymarket2026orders,
  ahoniemi2016overnight (tercile-k matches post-Lehman spillover),
  spdji2026indexmath, nasdaq2026totalview, nasdaq2026itchsamples,
  nyse2026taqimbalances.
- Must say: the exact frozen pipeline — gap = a0 + k·ES_gap, P(up) =
  Phi(mu/sigma(tau)), v1.2/v1.3 constants, inverse-variance fusion, bounded
  news voices, the replica formula — and that the strategy laboratory models
  execution (1c half-spread, impact, taker fees, volume gates) and survived an
  independent audit that removed four look-ahead/fill defects before any
  conclusion was drawn.

## results

- Target: 550–800 words. Prose deliberately thin: ~3 tables + 5 figures carry
  the numbers; after each float one paragraph reads the delta out
  ("committed accuracy rises from 80.9% to 81.5%" register).
- Content order + claims:
  - Accuracy ladder table (midnight→9:29) + ceiling: 21 [memory:spx-open-predictor-roadmap.md] [transcript:618d0dce];
    22 [memory:spx-open-predictor-roadmap.md] [repo:docs/approach.tex];
    23 [memory:spx-open-predictor-roadmap.md] [repo:config.py] [transcript:618d0dce].
    Hero figure `spx_open_predictor` gets its formal reference here.
  - Calibration results v1.2/v1.3 (table): 32 [memory:spx-open-predictor-roadmap.md];
    33 [memory:spx-open-predictor-roadmap.md]; 35 [memory:spx-open-predictor-roadmap.md];
    36 [memory:spx-open-predictor-roadmap.md] (per C6); 37 [memory:spx-open-predictor-roadmap.md];
    38 [memory:spx-open-predictor-roadmap.md] [repo:config.py]; 41 [memory:spx-open-predictor-roadmap.md]
    (465d caution, one sentence: 200d numbers are the validated reference).
  - Measured auction-feed sharpness (short block): 55 [memory:spx-open-predictor-roadmap.md];
    56 [memory:spx-open-predictor-roadmap.md] [transcript:380c3a0d];
    58 [memory:spx-open-predictor-roadmap.md] [transcript:618d0dce];
    61 [memory:spx-open-predictor-roadmap.md] [transcript:380c3a0d] (synthetic-only status stated).
  - Strategy results (table = survivor + graveyard): 70 [memory:polymarket-execution-microstructure.md] [transcript:380c3a0d] (per C1);
    71 [repo:docs/approach.tex] [memory:polymarket-execution-microstructure.md];
    72 [memory:polymarket-execution-microstructure.md] [transcript:380c3a0d] (per C2);
    73 [memory:polymarket-execution-microstructure.md] [repo:docs/approach.tex];
    75 [repo:docs/approach.tex] [memory:polymarket-execution-microstructure.md] [transcript:380c3a0d];
    76 [repo:docs/approach.tex] [transcript:380c3a0d]; 77 [repo:docs/approach.tex] [transcript:380c3a0d];
    78 [repo:docs/approach.tex] [transcript:380c3a0d]; 79 [transcript:380c3a0d];
    82 [repo:docs/approach.tex] [transcript:380c3a0d]; 83 [repo:docs/approach.tex] [memory:polymarket-execution-microstructure.md] [transcript:380c3a0d];
    85 [transcript:380c3a0d] (selectivity: 37 of 58 days sat out).
- Figures (manifest ids, in placement order): `spx_open_predictor_0000_200d`,
  `spx_open_predictor_0400_200d`, `spx_open_predictor_0000_confident`,
  `strategy_bankroll_50`, `stake_sweep`. (`spx_open_predictor` = hero, already
  on page 1; formally referenced here.)
- Citations available: polymarket2026spxmarket (market context in a caption at
  most); otherwise none — results cite own measurements.
- Must say: accuracy is a ladder, not a number — 72.5% at midnight to ~94% at
  9:29 against a 96.3% ceiling — and exactly one of 15 strategy candidates
  survives out-of-sample (hour-4 hold: $100→$135.92 at bet_frac 0.10;
  first_signal: $100→$321.53 flat $50 / $850.69 under the compounding rule),
  26W–2L on the test half, every number paired with its sizing rule.

## discussion

- Target: 1,500–1,900 words. Largest section. Subsections/blocks: miss
  anatomy; the two losses; quirk days and the crowd; the ceiling and the
  replica path; competitive landscape; negative results; limitations
  (\paragraph-headed blocks, generous — ~400–600 words of this section).
- Claims:
  - Miss anatomy: 27 [memory:spx-open-predictor-roadmap.md]; 28 [memory:spx-open-predictor-roadmap.md];
    29 [memory:spx-open-predictor-roadmap.md] [transcript:618d0dce]; 30 [memory:spx-open-predictor-roadmap.md];
    24 [transcript:618d0dce] (94% of midnight uncertainty is future news).
    Figure `spx_open_predictor_misses` placed here; hero re-referenced.
  - The two test losses, fully attributed: 81 [memory:polymarket-execution-microstructure.md] [transcript:380c3a0d]
    (per C7: Jul 10 = late futures flip; Jun 1/Jun 22 = true quirks).
  - Quirk days and the crowd: 8 [memory:spx-open-predictor-roadmap.md] [repo:docs/approach.tex];
    10 [transcript:618d0dce]; 25 [transcript:618d0dce] [repo:docs/approach.tex];
    36 [memory:spx-open-predictor-roadmap.md] (per C6); 117 [memory:spx-open-predictor-roadmap.md].
  - Ceiling → replica payoff: 22 [memory:spx-open-predictor-roadmap.md] [repo:docs/approach.tex];
    56 [memory:spx-open-predictor-roadmap.md] [transcript:380c3a0d];
    57 [memory:spx-open-predictor-roadmap.md]; 62 [repo:docs/approach.tex];
    64 [memory:spx-open-predictor-roadmap.md]; 65 [memory:spx-open-predictor-roadmap.md] (open fusion question — stated, not solved).
  - Competitive landscape / why the edge exists and persists:
    97 [memory:spx-open-predictor-roadmap.md]; 98 [memory:spx-open-predictor-roadmap.md];
    99 [memory:spx-open-predictor-roadmap.md]; 84 [transcript:380c3a0d] (hindsight ceiling);
    86 [transcript:380c3a0d] [memory:polymarket-execution-microstructure.md] (fee-era regime shift);
    94 [memory:polymarket-execution-microstructure.md] [transcript:380c3a0d] (maker posture; a 5c modeled
    edge is not 5c capturable).
  - Negative results (explicit block, list allowed ≤6 items or dense prose):
    117 [memory:spx-open-predictor-roadmap.md]; 118 [memory:spx-open-predictor-roadmap.md];
    119 [memory:spx-open-predictor-roadmap.md]; 120 [memory:spx-open-predictor-roadmap.md];
    121 [memory:spx-open-predictor-roadmap.md]; 122 [memory:polymarket-execution-microstructure.md] [repo:docs/approach.tex] [transcript:380c3a0d];
    123 [transcript:380c3a0d]; 124 [memory:spx-open-predictor-roadmap.md];
    125 [memory:spx-open-predictor-roadmap.md]; 74 [repo:docs/approach.tex] [transcript:380c3a0d]
    (dip-hunting refuted / adverse selection); 80 [transcript:380c3a0d] (midnight
    entry refuted); 49 [transcript:380c3a0d]; 50 [memory:spx-open-predictor-roadmap.md];
    51 [memory:spx-open-predictor-roadmap.md].
  - Limitations \paragraph blocks (each names its fix, then stops):
    88 [repo:docs/approach.tex] (one regime, 58 days, midpoint curves, declining
    volume, learning crowd); 41 [memory:spx-open-predictor-roadmap.md] (465d extension caution);
    61 [memory:spx-open-predictor-roadmap.md] [transcript:380c3a0d] (replica never saw real data);
    95 [memory:polymarket-execution-microstructure.md] (open execution unknowns);
    100 [repo:data_sources.md] [memory:wrds-access.md] + 101 [memory:wrds-access.md] +
    104 [memory:spx-open-predictor-roadmap.md] [transcript:bb4f31ad] [repo:data_sources.md]
    (academic licenses are research-only; production needs commercial data);
    53 [memory:spx-open-predictor-roadmap.md] + 126 [memory:spx-open-predictor-roadmap.md] [repo:data_sources.md] [transcript:195168b9] [transcript:bb4f31ad]
    (calendar and data-access blockers).
- Figures: `spx_open_predictor_misses`; re-reference `spx_open_predictor` (hero).
- Citations available: stollwhaley1990 (stale opens), ahoniemi2016overnight
  (vol-regime spillover), nasdaq2026totalview (NOII as best public predictor),
  databento2026equities, lseg2026tickhistory, wrds2026taq,
  nyse2026taqimbalances, polymarket2026orders, polymarket2026clob.
- Must say: every remaining miss is attributable — coin tosses, overnight news,
  or auction quirks; zero unexplained — which locates the model's boundary
  precisely at the ±6-point futures floor, and the auction replica (3–8x
  sharper in the final minute, measured) is the one priced path past it; the
  limitations are stated generously and none argued away.

## conclusion

- Target: 300–450 words. Free-standing (full-paper pattern per structure.md).
  No new numbers beyond restatement; no figures.
- Claims (restated, not re-derived): 11 [memory:spx-open-predictor-roadmap.md] [repo:docs/approach.tex];
  19 [memory:spx-open-predictor-roadmap.md] [repo:config.py] [repo:docs/approach.tex];
  21 [memory:spx-open-predictor-roadmap.md] [transcript:618d0dce];
  70 [memory:polymarket-execution-microstructure.md] [transcript:380c3a0d] (per C1);
  77 [repo:docs/approach.tex] [transcript:380c3a0d] (the ~$1k/day 1%-of-volume ceiling);
  86 [transcript:380c3a0d] [memory:polymarket-execution-microstructure.md] (monthly re-validation mandatory);
  87 [repo:docs/approach.tex] (the deployed 7-step rule, one sentence);
  62 [repo:docs/approach.tex] + 100 [repo:data_sources.md] [memory:wrds-access.md] (next step:
  the replica on real auction data).
- Figures: none.
- Citations available: none needed (optionally polymarket2026spxmarket).
- Must say: the crowd's k=1 assumption is measurably, persistently wrong; the
  resulting edge is real but small-scale — capped near $1k/day by the market's
  own liquidity — and conditional on monthly re-validation; the auction
  replica on real NOII/imbalance data is the identified next step, not a
  promise of more accuracy from the same inputs.

---

```json
{"sections": ["abstract", "introduction", "method", "results", "discussion", "conclusion"], "merged": [], "dropped": []}
```
