# The LLM News Layer

The news layer (`spx/news/`) gives the quant model a second voice: an LLM that
reads overnight headlines and macro context and outputs a small, bounded
adjustment to the futures-based prediction. It exists because a measured class
of losing days is news-driven: information arriving after the midnight
prediction hour flips or swings the gap. The layer never replaces the futures
model. Its output enters inverse-variance fusion with a floor on its own
uncertainty (`sigma_A >= 0.25%` in `spx/news/llm/prompt.py`), so it can nudge
and widen but never dominate.

The package has four subpackages: `sources/` (headline feeds), `llm/` (runner,
prompts, fitted weight), `eval/` (historical evaluation), and `ops/` (the
nightly jobs). All CLI entry points are wired in `spx/cli/newscmd.py`.

## Group A vs Group B

The layer splits work by how fast the input changes.

Group A is the slow context, fetched once per night at ~00:05 ET by
`spx/news/ops/prefetch.py`: tomorrow's 8:30 ET release names, the NFP-Friday
flag, and a baseline snapshot of Polymarket structural odds (economy and
geopolitics tags). One LLM call classifies this block into a volatility
multiplier `sigma_mult` in [1.0, 2.5] and a direction tilt capped at |0.3|.
Pre-event risk is symmetric, so direction is nonzero only for
nowcast-vs-consensus gaps or odds asymmetries. The empirical anchor: an NFP
morning should come out near 1.29 (fitted 2026-07-14 on 465 days, train half).

Group B is continuous headline classification between midnight and the open.
Scheduled checkpoints plus triggers feed the Group-B prompt with headlines
since the last run, odds deltas since the midnight baseline, and already-seen
story ids. Output: direction in [-1, +1], confidence, event type, a shock
flag, and a sigma multiplier in [1.0, 2.0].

By design neither group ever sees market prices, the ES gap, or the model's
position. That evidence already lives in the quant model, and showing it to
the LLM would only anchor it. Market moves act as run triggers, not as input.

## Sources (`spx/news/sources/`)

`gdelt.py` wraps the GDELT DOC 2.0 API: keyless, full archive back past 2015,
15-minute index cycle. `MARKET_QUERY` filters for tariff/fed/inflation/war/
opec-style macro stories. Hard rate limit: space calls at least 5s apart and
retry 429s with backoff. A verified timing fact drives the whole design: the
first Iran-strikes-halt article on 2026-03-23 was indexed the same hour ES
swung 2%, so publication and market effect are near-simultaneous. The LLM
must poll; it cannot read tomorrow's news early.

`alpaca.py` is the real-time wire: historical REST (stdlib urllib, paginated,
archive back to ~2015) and a live websocket (`NewsStream`, lazy
`websockets` import). Both normalize into one headline dict
`{id, headline, summary, symbols, created_at, url}` with `created_at` in ET.
Auth is a free key via `ALPACA_API_KEY` / `ALPACA_API_SECRET`.

## LLM stack (`spx/news/llm/`)

`runner.py` is provider-agnostic: any OpenAI-compatible chat-completions
endpoint (Gemini compat, Groq, OpenRouter, DeepSeek) configured through
`LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL`, with an optional
`LLM_FALLBACK_*` chain. Temperature 0.1, JSON response format, validate and
retry on bad output. Budget: ~12 calls per night (1 Group A plus at most 11
Group B), which fits the free tiers surveyed 2026-07.

`prompt.py` holds both system prompts and their validators. Each validator
parses the JSON and clamps every field to its bounds, so a misbehaving model
cannot push the fusion outside the fitted ranges.

`groupb.py` is the fitted mathematical weight behind the Group-B voice.
Because publication equals market effect, a repriced gap already contains the
news, and a naive directional voice would double-count. Two effects survive:
post-shock sigma (after a >= 0.35% one-hour gap move, residuals are wider:
`M_SHOCK = 1.32`, train half) and conflicted-day direction (shock happened
but |gap at 9:00| < 0.15%: the shock's sign predicted the official direction
87.0% of the time, n=23, encoded as `Z_CONFLICT = 0.85`, a 1-SE lower bound).
`voice()` applies the directional term only on conflicted days and the sigma
widening whenever a shock is recent (within 2 hours). Constants are fitted on
the train half only; retrain with `python3 . news-groupb-fit`.

## Eval suite (`spx/news/eval/`)

`mistakes.py` builds the eval set (`python3 . news-mistakes`): every day where
post-midnight information mattered, classed as `news_miss` (committed call
lost after a sign flip), `news_swing` (coin-flip day with a >= 0.35% swing),
or `news_survived` (committed call won despite a big swing). Quirk days,
where the gap held but the auction printed opposite, are excluded as
mechanics, not news. Output is cached at `.cache/news_mistakes.json`.

`timing.py` (`python3 . news-timing`) profiles when the decisive hour-over-
hour move hits. Moves spread across the whole night with 31% in the 8:00-9:00
ET hour, which is why the checkpoint schedule clusters late.

`event_labels.json` is a hand-verified inventory of the 14 largest mistake
days (Iran de-escalation 2026-03-23, Meta/Microsoft earnings 2025-10-30,
Russia doctrine 2024-11-19, tariff and CPI/NFP mornings), sourced from market-
day archives on 2026-07-14.

`replay.py` (`python3 . news-replay`) is the end-to-end test: for each labeled
day it fetches the GDELT snapshot ending at the first checkpoint after the
decisive move, runs the real Group-B prompt, and scores the LLM direction
against the move's actual sign (CORRECT / weak-right / missed(0) /
WRONG-SIGN). `replay_fetch.py` bulk-caches per-day snapshots for every
strategy day under `.cache/news_llm_replay/`, resumable, with no hindsight:
each window ends at its checkpoint. It also works around GDELT serving its
rate-limit page as HTTP 200 with zero articles, so empty results are retried.

`bench.py` (`python3 . news-llm-bench --models a,b,c`) scores candidate
models on 8 labeled cases built from the inventory (Iran headline, hot and
cool CPI, earnings miss, recap noise, conditional Fed speak, odds shock with
no headline, Russia doctrine). Scoring covers schema validity, direction
sign, shock flag, event type, and latency. `SHORTLIST` names 9 open-weight
candidates.

## Ops jobs (`spx/news/ops/`)

`prefetch.py` (`python3 . news-prefetch`) builds and caches the Group-A block
at `.cache/news_prefetch.json`. Three slots are placeholders awaiting
sources: `nowcast_cpi`, `consensus`, `earnings_after_close`. It also carries
the Group-B feed registry `STREAM_FEEDS`; of those five feeds only
`alpaca_news_ws` and `gdelt_sweep` have implementations under
`spx/news/sources/` today.

`schedule.py` defines the Group-B cadence as constants: six ET checkpoints
(02:30, 04:30, 07:00, 08:00, 08:35 mandatory after the 8:30 releases, 09:15),
per-feed polling cadence, three trigger rules (|ES gap change| >= 0.15% in 15
min, odds delta >= 5 pts vs baseline, >= 8 buffered articles in 15 min), and
a cap of 6 triggered runs per night on top of the 6 scheduled ones. No
daemon in the repo executes this schedule yet; it is the specification the
live loop will follow.

## Where to look

- `spx/news/llm/prompt.py`: both prompt contracts and their clamping validators
- `spx/news/llm/groupb.py`: the fitted Group-B weight and the fusion voice
- `spx/news/ops/prefetch.py`: Group-A block, feed registry, A/B rationale
- `spx/news/ops/schedule.py`: checkpoints, triggers, call budget
- `spx/news/eval/replay.py`: end-to-end historical replay on labeled days
- `spx/cli/newscmd.py`: every `news-*` CLI command in one file
