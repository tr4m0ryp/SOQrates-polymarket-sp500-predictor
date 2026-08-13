"""Futures-alone quirk-day baseline, scored three ways.

The replica evaluation in `tools/stage3_eval.py` scores DIRECTION ONLY, so a
like-for-like comparison needs the futures model scored the same way. The
paper quotes two other figures, and all three are reported here because they
answer different questions and are easy to confuse:

  direction   (p > 0.5) == official        comparable to the replica
  strict      confident AND correct         the paper's "2 of 12 strictly called"
  safe        low-confidence OR correct     the paper's "4 of 12 kept safe"

Restricted to the quirk days that also have a cached Databento pull, so the
two systems are compared over exactly the same dates.

    python3 tools/futures_baseline.py [--rebuild]
"""
import argparse
import glob
import json
import sys

sys.path.insert(0, ".")

import spx  # noqa: E402  (loads .env)
from spx.config import CACHE, CONF_COMMIT, QUIRK_DAYS  # noqa: E402
from spx.backtest import dataset  # noqa: E402
from spx.model.core import ModelV12, ModelV13, ModelProd  # noqa: E402

HOUR = 9          # 9:00 ET, the last hour the futures model is scored at


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--hour", type=int, default=HOUR)
    args = ap.parse_args()

    rows = dataset.load(rebuild=args.rebuild)
    train, _test = dataset.split(rows)
    print(f"dataset {len(rows)} days ({rows[0]['date']}..{rows[-1]['date']}), "
          f"train {len(train)}")

    pulled = {p.split("/")[-2] for p in glob.glob(".cache/databento/*/digest.json")}
    overlap = [r for r in rows if r["date"] in QUIRK_DAYS and r["date"] in pulled]
    print(f"quirk days with a Databento pull: {len(overlap)} "
          f"(of {len(QUIRK_DAYS)} known quirk days)\n")

    out = {}
    for model in (ModelV12().fit(train), ModelV13().fit(train),
                  ModelProd().fit(train)):
        d = s = safe = n = 0
        per_day = []
        for r in overlap:
            if args.hour not in r["es"]:
                continue
            _mu, _sig, p = model.predict(r, args.hour)
            up = r["off"] > 0
            correct = (p > 0.5) == up
            conf = max(p, 1 - p)
            committed = conf >= CONF_COMMIT
            n += 1
            d += correct
            s += committed and correct
            safe += (not committed) or correct
            per_day.append({"date": r["date"], "p_up": p, "off": r["off"],
                            "correct": correct, "committed": committed})
        print(f"{model.name:10} direction {d}/{n}   strict {s}/{n}   safe {safe}/{n}")
        out[model.name] = {"direction": d, "strict": s, "safe": safe, "n": n,
                           "days": per_day}

    art = CACHE / "futures_baseline.json"
    art.write_text(json.dumps({"hour": args.hour, "models": out}, indent=1))
    print(f"\nartifact: {art}")
    print("compare 'direction' against tools/stage3_eval.py, which scores the "
          "replica the same way.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
