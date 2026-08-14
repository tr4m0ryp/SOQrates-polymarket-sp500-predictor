"""Build per-day pre-open digests for every cached auction day.

The earlier digest stored each ticker's LAST indicative price regardless of
timestamp. Because the request window runs to 09:33, that silently included
post-open snapshots, and after the bell the indicative field equals the
realised cross. That is the lookahead defect that invalidated the first
stage-3 evaluation.

This writes `preopen.json` per day instead, holding only what was knowable at
09:29:59 ET, alongside the auction reference price and the realised cross for
scoring. Reading raw JSON is the slow part (~130 MB per day), so it is done
once and cached; the field is named differently from `digest.json` so the two
can never be confused.

    python3 tools/build_digests.py
"""
import datetime as dt
import glob
import json
import sys
from zoneinfo import ZoneInfo

sys.path.insert(0, ".")

import spx  # noqa: E402  (loads .env)
from spx.config import CACHE  # noqa: E402
from spx.replica.vendors.databento import source  # noqa: E402

NY = ZoneInfo("America/New_York")
CUTOFF = (9, 29, 59)


def build(date: str) -> dict | None:
    path = CACHE / "databento" / date / "preopen.json"
    if path.exists():
        return json.loads(path.read_text())
    try:
        snaps = source.snapshots(date)
    except Exception:                                   # noqa: BLE001
        return None
    if not snaps:
        return None
    y, m, d = (int(x) for x in date.split("-"))
    cut = int(dt.datetime(y, m, d, *CUTOFF, tzinfo=NY).timestamp() * 1e9)
    out = {"pred_preopen": {}, "ref": {}, "n_post_open_dropped": 0}
    for t, ss in snaps.items():
        ref = next((s.get("ref_price") for s in ss if s.get("ref_price")), None)
        if ref:
            out["ref"][t] = ref
        pre = [s for s in ss if s.get("pred_open") and s.get("ts_ns")
               and int(s["ts_ns"]) <= cut]
        post = [s for s in ss if s.get("pred_open") and s.get("ts_ns")
                and int(s["ts_ns"]) > cut]
        if post:
            out["n_post_open_dropped"] += 1
        if pre:
            out["pred_preopen"][t] = pre[-1]["pred_open"]
    try:
        out["cross"] = {t: px for t, (px, _ts) in source.prints(date).items()}
    except Exception:                                   # noqa: BLE001
        out["cross"] = {}
    path.write_text(json.dumps(out))
    return out


def main() -> int:
    days = sorted(p.split("/")[-2] for p in
                  glob.glob(".cache/databento/*/imbalance_NASDAQ.json"))
    print(f"{len(days)} cached auction days")
    done = skipped = 0
    for i, d in enumerate(days, 1):
        r = build(d)
        if r is None:
            skipped += 1
        else:
            done += 1
        if i % 20 == 0:
            print(f"  {i}/{len(days)} ({skipped} unusable)", flush=True)
    print(f"built {done}, unusable {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
