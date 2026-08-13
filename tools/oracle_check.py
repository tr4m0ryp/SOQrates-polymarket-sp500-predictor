"""Can perfect constituent auction data reconstruct the official index open?

This is the prerequisite test for the whole stage-3 family. It removes the
model entirely: every constituent's REALIZED opening cross price is used, so
there is no prediction and no timing uncertainty left. If the weighted
reconstruction still fails to track the official gap, the problem is not the
replica but the target, the weights, or the index arithmetic.

Ordinary and quirk days are reported separately and that split is the point.
Quirk days have a mean |official| of 0.045%; ordinary days about 0.37%. A
reconstruction that works on ordinary days and fails on quirk days says quirk
days are special. One that fails on both says the reconstruction is broken.

    python3 tools/oracle_check.py
"""
import glob
import json
import math
import sys

sys.path.insert(0, ".")

import spx  # noqa: E402  (loads .env)
from spx.config import CACHE, QUIRK_DAYS  # noqa: E402
from spx.data import weights as wmod, yahoo  # noqa: E402
from spx.replica.vendors.databento import source  # noqa: E402


def cross_digest(date: str) -> dict:
    """{ticker: cross_price} for a cached day, cached into the day digest."""
    path = CACHE / "databento" / date / "digest.json"
    dg = json.loads(path.read_text())
    if "cross" not in dg:
        dg["cross"] = {t: px for t, (px, _ts) in source.prints(date).items()}
        path.write_text(json.dumps(dg))
    return dg


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return float("nan")
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return float("nan")
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def main() -> int:
    days = sorted(p.split("/")[-2] for p in
                  glob.glob(".cache/databento/*/digest.json"))
    rows = wmod.load()
    W = {r["ticker"]: r["weight"] for r in rows}
    spx_hist = yahoo.daily_open_close("^GSPC", 400)
    idx = sorted(spx_hist)

    print(f"{'date':11} {'kind':9} {'oracle%':>9} {'official%':>10} "
          f"{'sign':>5} {'cover%':>7}")
    res = {"quirk": [], "ordinary": []}
    for d in days:
        if d not in spx_hist:
            continue
        dg = cross_digest(d)
        cross, ref = dg["cross"], dg["ref"]
        num = cov = 0.0
        for t, px in cross.items():
            r = ref.get(t)
            w = W.get(t)
            if not r or not w or not px:
                continue
            num += w * (px / r - 1) * 100
            cov += w
        if cov <= 0:
            continue
        oracle = num / cov            # weighted mean gap over covered names
        prev = idx[idx.index(d) - 1]
        official = (spx_hist[d][0] / spx_hist[prev][1] - 1) * 100
        kind = "quirk" if d in QUIRK_DAYS else "ordinary"
        ok = (oracle > 0) == (official > 0)
        res[kind].append((oracle, official, ok))
        print(f"{d} {kind:9} {oracle:>+8.3f}% {official:>+9.3f}% "
              f"{'OK' if ok else 'x':>5} {cov/sum(W.values())*100:>6.1f}%")

    print()
    for kind, rs in res.items():
        if not rs:
            continue
        o = [x[0] for x in rs]
        f = [x[1] for x in rs]
        hits = sum(1 for x in rs if x[2])
        mae = sum(abs(a - b) for a, b in zip(o, f)) / len(rs)
        mae0 = sum(abs(b) for b in f) / len(rs)
        print(f"{kind:9} n={len(rs):>3}  sign {hits}/{len(rs)}  "
              f"corr {pearson(o, f):>+.3f}  MAE {mae:.4f}%  "
              f"(predict-zero MAE {mae0:.4f}%)")

    out = CACHE / "oracle_check.json"
    out.write_text(json.dumps({k: [{"oracle": a, "official": b, "hit": c}
                                   for a, b, c in v] for k, v in res.items()},
                              indent=1))
    print(f"\nartifact: {out}")
    print("Reading: corr near +1 on ordinary days means the reconstruction is "
          "sound.\nA low or negative corr on ordinary days means the index "
          "arithmetic, the weights,\nor the official-open target is wrong, and "
          "no replica can be evaluated until it is fixed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
