# Stage 3: The Opening-Auction Replica

`spx/replica/` rebuilds the official first index tick from per-stock opening
auction data instead of inferring it from futures. Each exchange broadcasts an
indicative clearing price for every stock in the minutes before 9:30 (Nasdaq
NOII, NYSE imbalance feed). The replica takes those per-stock previews, asks
which stocks will actually print at 9:30:00 sharp, and assembles a distribution
over the index-level opening gap. The output (mean, sigma, P(up)) feeds the
same inverse-variance fusion as the futures model.

The venue asymmetry drives the whole design. Nasdaq's opening cross fires at
exactly 9:30:00 and its NOII indicative sits about 0 to 5 bp from the print at
9:29:50. NYSE opens are run by market makers and straggle by seconds to
minutes, with roughly 29 bp of indicative noise. So Nasdaq names enter the
replica at their indicative price, NYSE names default to prior close (stale,
contributing zero to the gap), and the interesting uncertainty is which NYSE
names sneak into the first tick.

## Core pieces (`spx/replica/core/`)

**Assembly** (`spx/replica/core/assembly.py`): the deterministic point
estimate. `first_tick_gap` computes `sum_i w_i * gap_i` over the names flagged
`in_first_tick`, in weighted-gap space where the index divisor cancels. Returns
the replica gap plus coverage diagnostics (live weight %, name counts).
`replica_sigma` is a placeholder uncertainty scaled by live weight.

**Monte Carlo** (`spx/replica/core/montecarlo.py`): the distributional
estimate that supersedes the point estimate for decisions. The photo gap is a
random variable: each stock contributes `w_i * B_i * g_i` where `B_i` is a
Bernoulli flip on whether the stock makes the first tick, correlated across
stocks by a common "slow morning" factor (logit shift, beta 1.0), plus
per-stock preview-vs-print noise (0.05% Nasdaq, 0.30% NYSE). `simulate` runs
2000 scenarios with fixed seed 7. Certain-live names collapse to one
deterministic base with pooled Gaussian noise; certain-stale names contribute
zero; only the 50 to 100 uncertain names are simulated. It also reports up to
6 pivotal names: stocks whose live/stale flip swings P(up) by more than 0.02.
`apply_prints` is the post-9:30 filtering step: observed prints become facts
with zero variance, and silent names get their p_live conditioned on "not
printed yet".

**Timing** (`spx/replica/core/timing.py`): per-stock p_live, the probability a
stock prints before the photo moment. Venue priors of 0.97 Nasdaq / 0.15 NYSE
apply to any ticker with no fitted samples. `fit_from_prints` replaces them
with empirical per-ticker delay samples persisted to
`.cache/print_delays.json`, and `condition_not_printed` is the Bayes update
used by `apply_prints`.

Measured against real Databento cross prints (2026-08-12, 17 ordinary days):
**96% of constituents print within 5 seconds of 9:30, median 0.93s**, so the
NYSE prior of 0.15 is far too pessimistic. Note the sample-size floor: p_live
is Laplace-smoothed as `(hits + 0.5) / (n + 1)`, so a single day caps any
ticker at 0.75 and a stable per-name estimate needs roughly 10 or more days.
Fit on ordinary days and evaluate on quirk days; sharing days between the two
leaks the answer into the model.

**Deviation** (`spx/replica/core/deviation.py`): measures how far the NOII
near price at 9:25/9:28/9:29/9:29:50 sits from the actual cross print, in bps,
per symbol and weight-aggregated to index level. This number is the replica's
accuracy ceiling. Runs on free ITCH sample files via the `noii-deviation` CLI
command.

**Pipeline glue** (`spx/replica/pipeline.py`): `build_constituents` merges
index weights with predicted opens and prior closes, `replica_estimate` wraps
assembly, `replica_distribution` wraps the Monte Carlo with the timing model,
and `fused_p_up` blends the replica with the futures view through
`spx/model/fusion.py`. One code path serves backtest (vendor pulls) and live
(streamed snapshots).

## Vendor stack (`spx/replica/vendors/`)

**Databento, primary** (`vendors/databento/`): datasets XNAS.ITCH (Nasdaq
NOII, history to 2018) and XNYS.PILLAR (NYSE imbalance, history about 2025+).
`client.py` is stdlib HTTP+JSON against the historical REST endpoint; live is
the one allowed exception, lazily importing `pip install databento` for the
binary DBN protocol. `schemas.py` normalizes both historical JSON and live DBN
objects through the same functions, so backtest and live yield identical
dicts; `pred_open` selection lives in exactly one place (`_indicative`).
`source.py` is the CLI bridge: `pull_day` fetches four data types (imbalance,
trades, mbp-1 quotes, both venues) over pre-open windows and caches raw JSON
under `.cache/databento/<date>/`; `snapshots`, `prints`, and `print_delays`
re-read that cache for stage3 and the timing model. `live.py` streams
imbalance records 9:28 to 9:30, one `databento.Live` client per dataset.

**LSEG, fallback** (`vendors/lseg/`): DataScope Select Tick History REST,
academic access, research-use only, historical only. `tick_history.py` does
the auth/extract/poll/download flow; `parse.py` turns the long-format FID CSV
into the same snapshot shape. Untested until `DSS_USERNAME`/`DSS_PASSWORD`
exist; the FID map is candidates to be confirmed with `discover()` on a first
real pull.

**ITCH raw files** (`vendors/itch/`): `parse.py` is a streaming binary parser
for Nasdaq TotalView-ITCH 5.0 that extracts only directory, NOII, and opening
cross messages, stopping at 09:45 ET. `samples.py` fetches Nasdaq's free
full-day captures (no key, 3.5 to 5.5 GB gzipped each, fixed scattered dates
mostly in 2019). This is what the deviation measurement runs on.

**NYSE TAQ raw files** (`vendors/taq/`): `parse.py` reads NYSE Order
Imbalances daily CSVs (message type 105, opening auction only); `samples.py`
fetches the few free sample days from NYSE's public directory. The paid feed
is $1,000/mo.

**Stitch, free live fallbacks** (`vendors/stitch/`): `webull.py` is the only
free live NOII leg, polling Webull's OpenAPI auction snapshot every 5 s across
9:28 to 9:30 with stdlib request signing (needs a funded Webull account,
Nasdaq names only). `feeds.py` holds `MassiveNYSEImbalance`, a live-only NYSE
imbalance websocket ($49/mo add-on, `MASSIVE_API_KEY`, needs `pip install
websockets`), plus an unimplemented NCDS Nasdaq stub. All normalize into the
same assembly-ready dicts.

## Command flow

```
python3 . databento-status              # key + dataset visibility check
python3 . databento-pull --date D       # cache raw JSON, dump observed fields
python3 . stage3 --date D               # replica vs official, uses the cache
```

`stage3` (in `spx/cli/auction.py`) defaults to databento when
`DATABENTO_API_KEY` is set, else LSEG (`lseg-pull --date D` first, cached as
`.cache/lseg/<date>.csv`). It takes each ticker's last snapshot with a
`pred_open`, fetches prior closes from Yahoo, runs both `replica_estimate` and
`replica_distribution`, and prints the gap, the distribution quantiles, the
pivotal names, and MATCH/MISS against the official ^GSPC open. `replica-sim`
is a data-free synthetic self-test of the Monte Carlo, and `noii-deviation
--file` runs the deviation stats on a raw ITCH file.

## Where to look

- `spx/replica/pipeline.py`: the whole stage-3 story in 80 lines, start here.
- `spx/replica/core/montecarlo.py`: the distributional assembly, pivotal
  names, and print filtering.
- `spx/replica/core/timing.py`: p_live, venue priors, and the Bayes update.
- `spx/replica/vendors/databento/source.py`: pull windows, cache layout, and
  the adapters stage3 actually calls.
- `spx/replica/vendors/databento/schemas.py`: DBN field maps and the single
  `pred_open` definition.
- `spx/cli/auction.py`: every replica CLI command, including `cmd_stage3`.
