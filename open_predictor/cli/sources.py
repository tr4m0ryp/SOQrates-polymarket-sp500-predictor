"""Data-source commands: weights, ground-truth, calendar-refresh."""


def cmd_ground_truth(_args):
    from open_predictor.sources.market import ground_truth
    bad = ground_truth.audit()
    if not bad:
        print("yahoo and stooq agree on every official open (tol 0.75 pts)")
    for b in bad:
        print(f"{b['date']}: yahoo {b['yahoo_open']:.2f} vs stooq "
              f"{b['stooq_open']:.2f}  (diff {b['diff_pts']:+.2f} pts)")


def cmd_weights(_args):
    from open_predictor.sources.market import weights
    rows = weights.load()
    rows.sort(key=lambda r: -r["weight"])
    print(f"{len(rows)} constituents; Nasdaq-listed share of weight: "
          f"{weights.nasdaq_share(rows)*100:.1f}%")
    for r in rows[:10]:
        print(f"  {r['ticker']:6} {r['weight']:5.2f}%  {r['exchange']}")


def cmd_calendar_refresh(_args):
    from open_predictor.sources.macro import releases
    try:
        out = releases.refresh()
    except RuntimeError as e:
        print(f"not ready: {e}")
        print("fallback active: NFP first-Friday rule (no key needed)")
        return
    for name, dates in out.items():
        print(f"{name}: {len(dates)} dates"
              + (f" (latest {dates[-1]})" if dates else ""))
