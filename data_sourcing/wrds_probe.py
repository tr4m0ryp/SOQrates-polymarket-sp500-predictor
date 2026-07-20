"""Probe WRDS for the datasets this project needs.

Run with the venv that has the wrds client:
    .venv-wrds/bin/python data_sourcing/wrds_probe.py

Requires a ~/.pgpass entry (create once, interactively:
    .venv-wrds/bin/python -c "import wrds; wrds.Connection().create_pgpass_file()"
). Writes .cache/wrds_probe.json with, per candidate table: whether it exists,
whether we can read it, its row count sample, columns, and date coverage.
"""
import json
import os
import sys

CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     ".cache")

# (library, table, why we want it, date column or None)
CANDIDATES = [
    # --- ground truth: the official S&P 500 open we resolve against ---
    ("comp", "idx_daily", "S&P 500 index daily OPEN/high/low/close (prcod!)", "datadate"),
    ("comp", "idxcst_his", "S&P 500 constituent membership history", "from"),
    ("crsp", "dsp500list", "CRSP S&P 500 membership intervals", "start"),
    ("crsp", "dsp500", "CRSP S&P 500 index daily series", "caldt"),
    ("crsp", "dsi", "CRSP daily market index series", "date"),
    # --- constituents: weights + prior closes for the replica ---
    ("crsp", "dsf", "CRSP daily stock file (prc, shrout, ret, openprc)", "date"),
    ("crsp", "dsenames", "PERMNO <-> ticker/exchange/SIC name history", "namedt"),
    ("crsp", "ccmxpf_lnkhist", "CRSP<->Compustat link (gvkey<->permno)", "linkdt"),
    ("comp", "secd", "Compustat security daily: prccd/prcod, cshoc shares", "datadate"),
    # --- volatility regime ---
    ("cboe", "cboe", "CBOE index daily (VIX family)", "date"),
    ("cboe", "vix", "VIX daily", "date"),
    # --- news layer: scheduled events ---
    ("ibes", "actu_epsus", "IBES actuals incl. announcement date/time", "anndats"),
    ("ibes", "statsum_epsus", "IBES consensus (surprise vs consensus)", "statpers"),
    ("comp", "co_ann", "Compustat announcement dates", "datadate"),
    # --- macro ---
    ("frb", "rates_daily", "Fed H.15 daily rates", "date"),
    # --- intraday / auction (expected: NO ACCESS at UvA) ---
    ("taqmsamp", "ctm_20030910", "TAQ millisecond sample trades", None),
    ("taqmsamp", "cqm_20030910", "TAQ millisecond sample quotes", None),
    ("taqm_2026", "ctm_20260710", "TAQ daily trades (needs taqm subscription)", None),
]


def probe(db, lib, table, date_col):
    out = {"library": lib, "table": table, "ok": False}
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
        print(f"{mark}{r['library']}.{r['table']:<18}{rng}  {r['why']}"
              + ("" if r["ok"] else f"  [{r.get('error','')}]"))
    print(f"\n{len(libs)} libraries visible; detail in .cache/wrds_probe.json")
    db.close()


if __name__ == "__main__":
    sys.exit(main())
