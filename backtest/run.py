"""Backtest runner: metrics table + quirk-day handling for each model."""
from config import CONF_COMMIT, QUIRK_DAYS
from model.core import Baseline, ModelV12, ModelV13
from backtest import dataset

EVAL_HOURS = (0, 4, 7, 9)


def metrics(model, test, h):
    br = n = hit = toss = comm = chit = oc80 = 0
    for r in test:
        if h not in r["es"]:
            continue
        _, _, p = model.predict(r, h)
        o = r["off"] > 0
        right = (p > 0.5) == o
        conf = max(p, 1 - p)
        br += (p - (1.0 if o else 0.0)) ** 2
        n += 1
        hit += right
        if conf < CONF_COMMIT:
            toss += 1
        else:
            comm += 1
            chit += right
        if conf >= 0.80 and not right:
            oc80 += 1
    return {"n": n, "brier": br / n, "acc": hit / n, "coinflip": toss / n,
            "comm_acc": chit / comm if comm else 0.0, "oc80": oc80}


def quirk_report(model, rows):
    lines, safe, tot = [], 0, 0
    for r in rows:
        if r["date"] not in QUIRK_DAYS or 9 not in r["es"]:
            continue
        _, _, p = model.predict(r, 9)
        o = r["off"] > 0
        conf = max(p, 1 - p)
        ok = conf < CONF_COMMIT or (p > 0.5) == o
        tot += 1
        safe += ok
        lines.append(f"  {r['date']} off {r['off']:+.3f}% P_up {p:.2f} "
                     f"{'safe' if ok else 'CONF-WRONG'}")
    return lines, safe, tot


def main(rebuild: bool = False):
    rows = dataset.load(rebuild)
    train, test = dataset.split(rows)
    print(f"dataset: {len(rows)} days ({rows[0]['date']}..{rows[-1]['date']}), "
          f"train {len(train)} / test {len(test)}")

    models = [Baseline().fit(train), ModelV12().fit(train), ModelV13().fit(train)]
    print(f"\n{'model':10}{'h':>3} {'Brier':>8} {'acc':>7} {'coinflip':>9} "
          f"{'commAcc':>8} {'oc80':>5}")
    for m in models:
        for h in EVAL_HOURS:
            s = metrics(m, test, h)
            print(f"{m.name:10}{h:>3} {s['brier']:8.4f} {s['acc']*100:6.1f}% "
                  f"{s['coinflip']*100:8.1f}% {s['comm_acc']*100:7.1f}% "
                  f"{s['oc80']:>5}")

    best = models[-1]
    lines, safe, tot = quirk_report(best, rows)
    print(f"\nquirk days at 9:00 under {best.name} ({safe}/{tot} safe):")
    print("\n".join(lines))
    print("\nnote: quirk direction is unfixable from futures data - "
          "requires the Databento auction replica (stage 3).")
