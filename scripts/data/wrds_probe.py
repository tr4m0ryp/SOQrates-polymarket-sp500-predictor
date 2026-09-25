"""Probe WRDS for the datasets this project needs.

Run with the venv that has the wrds client:
    .venv-wrds/bin/python scripts/data/wrds_probe.py

Requires a ~/.pgpass entry (create once, interactively:
    .venv-wrds/bin/python -c "import wrds; wrds.Connection().create_pgpass_file()"
). Writes .cache/wrds_probe.json with, per candidate table: whether it exists,
whether we can read it, its row count sample, columns, and date coverage.
"""
import json
import os
import sys

CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                     ".cache")

# The datasets this project needs, as (library, table, why, date column).
# Grouped by the job each one does; probe reports access + coverage per row.
CANDIDATES = [
    # --- A. ground truth: the official S&P 500 open we resolve against ---
    ("comp", "idx_daily", "A1 S&P500 index daily incl. OPEN (prcod) - ground truth", "datadate"),
    ("comp", "idxsp_hist", "A2 index-code history (gvkeyx for S&P 500)", None),
    ("crsp", "dsp500", "A3 CRSP S&P500 daily level/return (cross-check)", "caldt"),
    ("crsp", "dsi", "A4 CRSP daily market index (cross-check)", "date"),
    # --- B. constituents: membership, weights, venue tag, prior closes ---
    ("comp", "idxcst_his", "B1 S&P500 membership history (gvkey, from/thru)", "from"),
    ("crsp", "dsp500list", "B2 CRSP S&P500 membership intervals (permno)", "start"),
    ("crsp", "dsf", "B3 daily stock file: prc, openprc, shrout, cfacpr", "date"),
    ("crsp", "dsenames", "B4 permno->ticker/exchcd (NYSE vs Nasdaq venue tag)", "namedt"),
    ("crsp", "ccmxpf_lnkhist", "B5 gvkey<->permno link", "linkdt"),
    ("comp", "secd", "B6 Compustat security daily: prccd/prcod, cshoc", "datadate"),
    # --- C. volatility regime (sigma scaler inputs) ---
    ("cboe", "cboe", "C1 CBOE index daily - VIX family", "date"),
    ("cboe", "vix", "C2 VIX daily (alt table name)", "date"),
    # --- D. news layer: scheduled events, consensus, surprises ---
    ("ibes", "actu_epsus", "D1 IBES actuals + announcement date/time", "anndats"),
    ("ibes", "statsum_epsus", "D2 IBES consensus -> surprise sign", "statpers"),
    ("comp", "fundq", "D3 Compustat quarterly incl. report date rdq", "rdq"),
    ("frb", "rates_daily", "D4 Fed H.15 daily rates (regime context)", "date"),
    # --- E. auction layer (expect NO ACCESS - documents the gap) ---
    ("taqmsamp", None, "E1 TAQ millisecond SAMPLE - which dates exist?", None),
    ("taqm_2026", None, "E2 TAQ daily 2026 (needs taqm_common - expect denied)", None),
]


def probe(db, lib, table, date_col):
    out = {"library": lib, "table": table, "ok": False}
    if table is None:                            # library-level probe
        try:
            tabs = db.list_tables(library=lib)
            out.update(ok=True, n_tables=len(tabs), tables=sorted(tabs)[:25])
        except Exception as e:                   # noqa: BLE001
            out["error"] = str(e).split("\n")[0][:160]
        return out
    try:
        cols = db.describe_table(library=lib, table=table)
        out["ok"] = True
        out["ncols"] = len(cols)
        out["columns"] = list(cols["name"])[:40] if hasattr(cols, "columns") else None
    except Exception as e:                       # noqa: BLE001 - report, don't raise
        out["error"] = str(e).split("\n")[0][:160]
        return out
    if date_col:
        try:
            q = f"select min({date_col}) as lo, max({date_col}) as hi from {lib}.{table}"
            r = db.raw_sql(q)
            out["range"] = [str(r.iloc[0]["lo"]), str(r.iloc[0]["hi"])]
        except Exception as e:                   # noqa: BLE001
            out["range_error"] = str(e).split("\n")[0][:120]
    return out


def main():
    import wrds
    db = wrds.Connection()
    libs = sorted(db.list_libraries())
    results = [probe(db, lib, tbl, dc) for lib, tbl, _, dc in CANDIDATES]
    payload = {"n_libraries": len(libs), "libraries": libs,
               "candidates": [{**r, "why": why}
                              for r, (_, _, why, _) in zip(results, CANDIDATES)]}
    os.makedirs(CACHE, exist_ok=True)
    with open(os.path.join(CACHE, "wrds_probe.json"), "w") as f:
        json.dump(payload, f, indent=1)
    for r in payload["candidates"]:
        mark = "OK " if r["ok"] else "NO "
        rng = f" {r.get('range')}" if r.get("range") else ""
        name = f"{r['library']}.{r['table'] or '*'}"
        extra = f" ({r['n_tables']} tables)" if r.get("n_tables") else ""
        print(f"{mark}{name:<26}{rng}{extra}  {r['why']}"
              + ("" if r["ok"] else f"  [{r.get('error','')}]"))
    print(f"\n{len(libs)} libraries visible; detail in .cache/wrds_probe.json")
    db.close()


if __name__ == "__main__":
    sys.exit(main())
