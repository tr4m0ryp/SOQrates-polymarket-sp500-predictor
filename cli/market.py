"""Model-facing commands: backtest, predict, quirks."""
import datetime as dt
import time

from config import NY


def cmd_backtest(args):
    from backtest import run
    run.main(rebuild=args.rebuild)


def cmd_predict(_args):
    from backtest import dataset
    from data import futures
    from model.core import ModelV13
    from macro import releases
    from pm import gamma, edge

    rows = dataset.load()
    model = ModelV13().fit(rows)
    feeds = futures.load_feeds()
    now = int(time.time())
    prior = rows[-1]["date"]
    today = dt.datetime.now(NY).date()

    es = futures.live_gap(feeds["ES=F"], prior, now)
    nq = futures.live_gap(feeds["NQ=F"], prior, now)
    if es is None:
        print("no live ES price (market closed window?)")
        return
    hour = min(max(dt.datetime.now(NY).hour, 0), 9)
    # regime fields (EWMA/RV) come from the last completed day's row
    row = {**rows[-1], "es": {hour: es},
           "nq": {hour: nq if nq is not None else es}, "ym": {},
           "release_morning": releases.is_release_morning(today)}
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
    from backtest import dataset, run
    from model.core import ModelV13
    rows = dataset.load()
    train, _ = dataset.split(rows)
    lines, safe, tot = run.quirk_report(ModelV13().fit(train), rows)
    print(f"quirk days ({safe}/{tot} safe):")
    print("\n".join(lines))
