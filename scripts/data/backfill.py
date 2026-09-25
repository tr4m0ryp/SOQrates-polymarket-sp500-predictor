"""Capped, resumable Databento backfill.

Pulls a list of trading days under the spend cap enforced in
`open_predictor.forecast.auction.vendors.databento.transport.budget`, skipping days already cached so a
re-run costs nothing. Quirk days come first (C6), then ordinary days for the
print-delay fit.

    python3 scripts/data/backfill.py --days 30
    python3 scripts/data/backfill.py --dates 2026-07-10,2026-06-22
"""
import argparse
import sys

sys.path.insert(0, ".")

import open_predictor  # noqa: E402  (loads .env)
from open_predictor.config import QUIRK_DAYS  # noqa: E402
from open_predictor.sources.market import yahoo  # noqa: E402
from open_predictor.forecast.auction.vendors.databento import source  # noqa: E402
from open_predictor.forecast.auction.vendors.databento.transport import budget  # noqa: E402


def trading_days(n: int) -> list[str]:
    """Most recent `n` trading days, newest last, from the index history."""
    return sorted(yahoo.daily_open_close("^GSPC", 400))[-n:]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=0,
                    help="ordinary trading days to add after the quirk days")
    ap.add_argument("--dates", default="", help="explicit comma-separated list")
    args = ap.parse_args()

    if args.dates:
        wanted = [d.strip() for d in args.dates.split(",") if d.strip()]
    else:
        wanted = list(QUIRK_DAYS)
        if args.days:
            for d in reversed(trading_days(args.days + len(QUIRK_DAYS))):
                if d not in wanted:
                    wanted.append(d)
                if len(wanted) >= len(QUIRK_DAYS) + args.days:
                    break

    todo = [d for d in wanted if not source.cached(d)]
    print(f"{len(wanted)} days requested, {len(wanted)-len(todo)} already cached, "
          f"{len(todo)} to pull")
    print(f"budget: ${budget.spent_usd():.4f} spent of ${budget.cap_usd():.2f}\n")

    done = failed = 0
    for i, date in enumerate(todo, 1):
        try:
            res = source.pull_day(date)
        except Exception as e:                      # noqa: BLE001
            print(f"[{i}/{len(todo)}] {date} ERROR {type(e).__name__}: {e}")
            failed += 1
            continue
        budget_hits = [k for k, v in res["errors"].items()
                       if str(v).startswith("BUDGET")]
        if budget_hits:
            print(f"[{i}/{len(todo)}] {date} STOPPED: spend cap reached")
            failed += 1
            break
        n = sum(res["counts"].values())
        print(f"[{i}/{len(todo)}] {date} {n:>7} records  ${res['cost_usd']:.4f}  "
              f"(total ${res['spent_usd']:.2f})"
              + (f"  errors={list(res['errors'])}" if res["errors"] else ""))
        done += 1

    print(f"\npulled {done}, failed {failed}, "
          f"spend ${budget.spent_usd():.4f} of ${budget.cap_usd():.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
