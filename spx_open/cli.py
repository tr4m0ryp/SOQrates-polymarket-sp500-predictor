"""CLI: backtest | predict | quirks | ground-truth | weights | calendar-refresh."""
import argparse
import datetime as dt
import time

from .config import NY


def cmd_backtest(args):
    from .backtest import run
    run.main(rebuild=args.rebuild)


def cmd_predict(_args):
    from .backtest import dataset
    from .data import futures
    from .model.core import ModelV13
    from .macro import releases
    from .pm import gamma, edge

    rows = dataset.load()
    model = ModelV13().fit(rows)          # fit on all history for live use
    feeds = futures.load_feeds()
    now = int(time.time())
    prior = rows[-1]["date"]              # last completed trading day
    today = dt.datetime.now(NY).date()

    es = futures.live_gap(feeds["ES=F"], prior, now)
    nq = futures.live_gap(feeds["NQ=F"], prior, now)
    if es is None:
        print("no live ES price (market closed window?)")
        return
    hour = min(max(dt.datetime.now(NY).hour, 0), 9)
    row = {**rows[-1], "es": {hour: es}, "nq": {hour: nq if nq is not None else es},
           "ym": {}, "release_morning": releases.is_release_morning(today)}
    mu, sig, p = model.predict(row, hour)
    print(f"now (ET hour {hour}): ES gap {es:+.2f}%  NQ-ES "
          f"{(nq - es) if nq is not None else 0:+.2f}%")
    print(f"predicted official gap {mu:+.3f}% +- {sig:.3f}%  ->  P(up) {p:.2f}")
    if row["release_morning"]:
        print("8:30 release morning - sigma widened, expect a jump at 8:30")

    market = gamma.open_market(today)
    if market and not market["closed"]:
        verdict = edge.assess(p, market["p_up"])
        print(f"polymarket P(up) {market['p_up']}  vol ${market['volume']:,.0f} "
              f"liq ${market['liquidity']:,.0f}")
        print(f"-> {verdict['action']}"
              + (f" (edge {verdict['edge']:+.2f})" if verdict["edge"] else ""))
    else:
        print("no open Polymarket market for today")


def cmd_quirks(_args):
    from .backtest import dataset, run
    from .model.core import ModelV13
    rows = dataset.load()
    train, _ = dataset.split(rows)
    lines, safe, tot = run.quirk_report(ModelV13().fit(train), rows)
    print(f"quirk days ({safe}/{tot} safe):")
    print("\n".join(lines))


def cmd_ground_truth(_args):
    from .data import ground_truth
    bad = ground_truth.audit()
    if not bad:
        print("yahoo and stooq agree on every official open (tol 0.75 pts)")
    for b in bad:
        print(f"{b['date']}: yahoo {b['yahoo_open']:.2f} vs stooq "
              f"{b['stooq_open']:.2f}  (diff {b['diff_pts']:+.2f} pts)")


def cmd_weights(_args):
    from .data import weights
    rows = weights.load()
    rows.sort(key=lambda r: -r["weight"])
    print(f"{len(rows)} constituents; Nasdaq-listed share of weight: "
          f"{weights.nasdaq_share(rows)*100:.1f}%")
    for r in rows[:10]:
        print(f"  {r['ticker']:6} {r['weight']:5.2f}%  {r['exchange']}")


def cmd_noii_deviation(args):
    from .replica import itch, deviation
    from .data import weights as wmod
    try:
        w = {r["ticker"]: r["weight"] for r in wmod.load()}
    except Exception:
        w = {}

    def progress(n, ts_ns):
        h = ts_ns / 3_600_000_000_000
        print(f"  ...{n/1e6:.0f}M msgs, stream at {int(h):02d}:{int(h%1*60):02d} ET")

    print(f"parsing {args.file} (stops after opening cross window)")
    records = itch.parse_opening(args.file, progress=progress)
    agg = deviation.aggregate(records, weights=w)
    print(f"\nsymbols with opening cross + NOII: "
          f"{sum(1 for r in agg['per_symbol'] if r)}")
    print(f"\n{'checkpoint':>9} {'n':>6} {'median|dev|':>11} {'mean|dev|':>10} "
          f"{'p90|dev|':>9} {'idx signed':>10} {'cover%':>7}")
    for cp, s in agg["stats"].items():
        print(f"{cp:>9} {s['n']:>6} {s['median_abs_bps']:>9.1f}bp "
              f"{s['mean_abs_bps']:>8.1f}bp {s['p90_abs_bps']:>7.1f}bp "
              f"{s.get('index_signed_bps', float('nan')):>8.2f}bp "
              f"{s.get('covered_weight_pct', 0):>6.1f}%")
    megas = [r for r in agg["per_symbol"]
             if r["ticker"] in ("AAPL", "MSFT", "AMZN", "GOOGL", "FB", "META",
                                "NVDA", "TSLA", "INTC", "CSCO")]
    if megas:
        print("\nmega-caps, near-price deviation vs print (bps):")
        for r in sorted(megas, key=lambda x: x["ticker"]):
            vals = " ".join(f"{cp}:{r[cp]:+.1f}" if r[cp] is not None else f"{cp}:-"
                            for cp in ("9:25", "9:28", "9:29", "9:29:50"))
            print(f"  {r['ticker']:6} cross {r['cross']:>9.2f}  {vals}")


def cmd_lseg_status(_args):
    from .replica import lseg_tick_history as lseg
    try:
        lseg.auth_token()
        print("DataScope Select credentials OK - token issued.")
        print("Next: spx_open lseg pull via replica.lseg_tick_history."
              "quirk_day_pull(tickers, tickers, 'YYYY-MM-DD')")
    except lseg.LsegError as e:
        print(f"not ready: {e}")
    except Exception as e:
        print(f"auth failed: {e}")


def cmd_calendar_refresh(_args):
    from .macro import releases
    out = releases.refresh()
    for name, dates in out.items():
        print(f"{name}: {len(dates)} dates" + (f" (latest {dates[-1]})" if dates else ""))


def main():
    ap = argparse.ArgumentParser(prog="spx_open")
    sub = ap.add_subparsers(dest="cmd", required=True)
    bt = sub.add_parser("backtest")
    bt.add_argument("--rebuild", action="store_true")
    bt.set_defaults(fn=cmd_backtest)
    nd = sub.add_parser("noii-deviation")
    nd.add_argument("--file", required=True,
                    help="path to a NASDAQ_ITCH50.gz full-day file")
    nd.set_defaults(fn=cmd_noii_deviation)
    for name, fn in (("predict", cmd_predict), ("quirks", cmd_quirks),
                     ("ground-truth", cmd_ground_truth),
                     ("weights", cmd_weights),
                     ("lseg-status", cmd_lseg_status),
                     ("calendar-refresh", cmd_calendar_refresh)):
        sub.add_parser(name).set_defaults(fn=fn)
    args = ap.parse_args()
    args.fn(args)
