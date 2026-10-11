# 13. Columnar store for the Databento pulls

**Verdict: useful for one job, rebuilding digests.** Live prediction, the backtest and the
strategy sim read the ~22 KB per-day digests (`preopen.json`, `digest.json`) and gain
nothing. Every change to a digest rule re-parses 21 GB of raw Databento JSON, which takes
~20 minutes. That has happened twice already: the cross moved from "earliest trade" to
"largest trade", and `digest` was replaced by `preopen` with a cutoff after it leaked
post-open data. A Parquet copy turns that into seconds and ~10-20x less disk.

Do it when another round of digest-rule research is planned. Skip it otherwise.

## What to convert

| Data | Now | Target |
|---|---|---|
| `.cache/databento/<date>/trades_{NASDAQ,NYSE}.json` | 13.9 GB, 294 files, flat record lists | `trades/date=<date>/venue=<v>.parquet` |
| `.cache/databento/<date>/imbalance_{NYSE,NASDAQ}.json` | 6.0 GB, 296 files | `imbalance/date=<date>/venue=<v>.parquet` |
| `.cache/databento/<date>/mbp-1_*.json` | 1.2 GB, never read by code | skip; archive (zstd) if disk is needed |
| `pm_history/`, `news_archive/`, digests | small | skip |

Sort each file by `(symbol, ts_event)`. Flatten `hd.*` and `levels[0].*` to top-level columns,
as `spx/replica/vendors/databento/schemas.py` already does in Python.

## Where the code goes

- The converter lives in `tools/` and runs in a **separate venv** (the `.venv-wrds`
  precedent): core `spx/` stays stdlib-only. duckdb and pyarrow are not installed in the
  core environment.
- `spx/replica/vendors/databento/source.py:_read` stays the JSON path. A Parquet fast path
  may be added behind an existence check, never as a replacement.
- Any change to the data flow updates `05-replica.md` and `11-conventions-and-environment.md`
  in the same commit.

## Exactness rules

- **Prices are fixed-point 1e-9 strings.** Store them as `BIGINT` (or `DECIMAL(18,9)`), never
  `DOUBLE`. `_px` in `schemas.py` divides by 1e9 into a float; parity tests compare against
  that output.
- **Timestamps are nanoseconds.** Store `BIGINT` ns; DuckDB `TIMESTAMPTZ` keeps only
  microseconds. Convert to ET (`America/New_York`) at query time.
- **Point-in-time is `hd.ts_event`**, not `ts_recv` (~200 µs later). Keep both columns; the
  cutoff logic must keep using `ts_event`.
- **`"0"` is a null sentinel** in imbalance records and must become NULL, so the `pred_open`
  fallback chain (`ind_match_price` -> `cont_book_clr_price` -> `ref_price`) still works.
- **Never read with type inference.** Use `read_json(..., columns={...})` with explicit types.

## Contract

1. The raw JSON stays. It cost $39.49 across 888 priced pulls; it is not "derived data,
   delete to rebuild", whatever the cache docs say.
2. Verify every converted day row by row against `json.load` of its source.
3. Before trusting Parquet, rebuild `preopen.json` and `digest.json` from it and require them
   byte-identical to the JSON-built ones.

Sketch of the per-day query a new rule becomes:

```sql
SELECT symbol, arg_max(ind_match_price, ts_event) AS last_indicative
FROM read_parquet('.cache/columnar/imbalance/date=*/venue=*.parquet', hive_partitioning = true)
WHERE ts_event <= cutoff_ns(date)       -- 09:29:59 ET in ns
GROUP BY date, symbol;
```

## References

- Method, measured gains and pitfalls: `~/.claude/memory/feedback/workflow/large-data-columnar.md`.
- Reusable converter and verifier (copy-then-extend): `~/projects/trenches/src/store/`
  (`jsonl/` infers a lossless plan for any JSON lines; adapt it for JSON arrays).
- Engine: stock DuckDB 1.5.x, or the fork `github.com/tr4m0ryp/duckdb` (exact, faster
  `sum`/`avg` over unsigned 64-bit).
