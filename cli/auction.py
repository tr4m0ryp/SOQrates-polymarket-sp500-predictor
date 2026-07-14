"""Auction-replica commands: noii-deviation, lseg-*, stage3."""


def cmd_noii_deviation(args):
    from replica import itch, deviation
    from data import weights as wmod
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
    from replica import lseg_tick_history as lseg
    try:
        lseg.auth_token()
        print("DataScope Select credentials OK - token issued.")
    except lseg.LsegError as e:
        print(f"not ready: {e}")
    except Exception as e:
        print(f"auth failed: {e}")


def cmd_lseg_pull(args):
    from config import CACHE
    from data import weights as wmod
    from replica import lseg_tick_history as lseg, lseg_parse

    rows = wmod.load()
    nas = [r["ticker"] for r in rows if r["exchange"] == "NASDAQ"]
    nyse = [r["ticker"] for r in rows if r["exchange"] == "NYSE"]
    print(f"pulling {args.date}: {len(nas)} Nasdaq + {len(nyse)} NYSE RICs")
    payload = lseg.quirk_day_pull(nas, nyse, args.date)
    out = CACHE / "lseg"
    out.mkdir(exist_ok=True)
    path = out / f"{args.date}.csv"
    path.write_bytes(payload)
    print(f"saved {path} ({len(payload)/1e6:.1f} MB)")
    print("\ntop FIDs seen (extend lseg_parse.FID_MAP with auction fields):")
    for name, n in list(lseg_parse.discover(payload).items())[:25]:
        print(f"  {name}: {n}")


def cmd_stage3(args):
    from config import CACHE
    from data import yahoo
    from replica import lseg_parse, pipeline

    path = CACHE / "lseg" / f"{args.date}.csv"
    if not path.exists():
        print(f"no cached pull for {args.date} - run: lseg-pull --date {args.date}")
        return
    snaps = lseg_parse.snapshots(str(path))
    pred = {}
    for t, ss in snaps.items():
        last = next((s for s in reversed(ss) if s.get("pred_open")), None)
        if last:
            pred[t] = last["pred_open"]
    print(f"{len(pred)} tickers with indicative prices")
    spx = yahoo.daily_open_close("^GSPC", 400)
    days = sorted(spx)
    if args.date not in spx:
        print(f"{args.date} not a trading day in ^GSPC history")
        return
    prior = days[days.index(args.date) - 1]
    closes = {}
    for t in pred:
        try:
            d = yahoo.daily_open_close(t.replace(".", "-"), 35)
            closes[t] = d.get(prior, (None, None))[1]
        except Exception:
            continue
    closes = {t: c for t, c in closes.items() if c}
    rep = pipeline.replica_estimate(pred, closes)
    official = (spx[args.date][0] / spx[prior][1] - 1) * 100
    print(f"replica gap {rep['replica_gap_pct']:+.3f}% "
          f"(live weight {rep['live_weight_pct']:.0f}%, sigma {rep['sigma_pct']:.3f}%)")
    print(f"official gap {official:+.3f}%  -> direction "
          f"{'MATCH' if (rep['replica_gap_pct'] > 0) == (official > 0) else 'MISS'}")
