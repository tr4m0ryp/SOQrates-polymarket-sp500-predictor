"""Stage-3 replica evaluation across every cached Databento day.

Fits the per-stock print-delay model on ORDINARY days only, then evaluates the
auction replica on the QUIRK days it must call. Fitting and evaluation never
share a day, so the quirk-day number is out of sample.

Prior closes are fetched once per ticker (a full history covers every date)
and cached to `.cache/prior_closes.json`; the per-day CLI path refetches per
ticker per day and is far too slow for a multi-day sweep.

    python3 tools/stage3_eval.py            # fit on ordinary, score quirks
    python3 tools/stage3_eval.py --refresh  # rebuild the prior-close cache
"""
import argparse
import json
import sys

sys.path.insert(0, ".")

import spx  # noqa: E402  (loads .env)
from spx.config import CACHE, QUIRK_DAYS  # noqa: E402
from spx.data import weights as wmod, yahoo  # noqa: E402
from spx.replica import pipeline  # noqa: E402
from spx.replica.core.timing import TimingModel  # noqa: E402
from spx.replica.vendors.databento import source  # noqa: E402

PRICES = CACHE / "prior_closes.json"


def digest(date: str) -> dict:
    """Small per-day summary, computed once and cached beside the raw pull.

    The raw JSON for one day is ~130 MB across six slices, and re-parsing 29
    days of it on every evaluation costs more than 15 minutes. Everything
    downstream needs only three numbers per ticker, so they are precomputed
    here and written to `digest.json` next to the raw files. Writing per day
    makes a long build resumable.
    """
    path = CACHE / "databento" / date / "digest.json"
    if path.exists():
        return json.loads(path.read_text())
    snaps = source.snapshots(date)
    out = {"pred": {}, "ref": {}}
    for t, ss in snaps.items():
        last = next((s for s in reversed(ss) if s.get("pred_open")), None)
        ref = next((s.get("ref_price") for s in ss if s.get("ref_price")), None)
        if last:
            out["pred"][t] = last["pred_open"]
        if ref:
            out["ref"][t] = ref
    out["delays"] = source.print_delays(date)
    path.write_text(json.dumps(out))
    return out


def cached_days() -> list[str]:
    d = CACHE / "databento"
    return sorted(p.name for p in d.iterdir()
                  if p.is_dir() and source.cached(p.name)) if d.exists() else []


def build_price_cache(tickers, refresh=False) -> dict:
    if PRICES.exists() and not refresh:
        return json.loads(PRICES.read_text())
    out, fail = {}, 0
    for i, t in enumerate(sorted(tickers), 1):
        try:
            hist = yahoo.daily_open_close(t.replace(".", "-"), 400)
            out[t] = {d: v[1] for d, v in hist.items() if v and v[1]}
        except Exception:                              # noqa: BLE001
            fail += 1
        if i % 100 == 0:
            print(f"  prices {i}/{len(tickers)} ({fail} failed)", flush=True)
    PRICES.write_text(json.dumps(out))
    print(f"  price cache built: {len(out)} tickers, {fail} failed")
    return out


def prior_close(prices, ticker, date, index_days):
    """Close on the trading day before `date`, from the cached history.

    FALLBACK ONLY. Yahoo history is split-adjusted while Databento prices are
    raw and contemporaneous, so this is wrong by the cumulative split factor
    for any name that split since `date` (measured 2025-09-12: NFLX +899%,
    BKNG +2383%). Prefer `auction_reference` below.
    """
    h = prices.get(ticker)
    if not h:
        return None
    i = index_days.index(date)
    for back in range(1, 6):                    # tolerate per-name gaps
        if i - back < 0:
            return None
        c = h.get(index_days[i - back])
        if c:
            return c
    return None


def auction_reference(snaps_for_ticker):
    """The auction's own reference price: contemporaneous and split-correct.

    Exchanges publish the auction reference (prior close adjusted for
    corporate actions) inside the imbalance record itself, so pairing it with
    the same record's indicative price removes every adjustment mismatch and
    the need to fetch prior closes at all.
    """
    for s in snaps_for_ticker:
        if s.get("ref_price"):
            return s["ref_price"]
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()

    days = cached_days()
    quirks = [d for d in days if d in QUIRK_DAYS]
    ordinary = [d for d in days if d not in QUIRK_DAYS]
    print(f"cached: {len(days)} days | quirk {len(quirks)} | ordinary {len(ordinary)}")

    rows = wmod.load()
    venues = {r["ticker"]: r["exchange"] for r in rows}
    prices = build_price_cache([r["ticker"] for r in rows], args.refresh)

    spx_hist = yahoo.daily_open_close("^GSPC", 400)
    index_days = sorted(spx_hist)

    # --- fit timing on ordinary days ONLY (out-of-sample for quirks) --------
    tm = TimingModel(venues=venues)
    tm.fit_from_prints({d: digest(d)["delays"] for d in ordinary})
    pl = [tm.p_live(r["ticker"]) for r in rows]
    wsum = sum(r["weight"] for r in rows)
    lw = sum(r["weight"] * tm.p_live(r["ticker"]) for r in rows) / wsum * 100
    print(f"timing fitted on {len(ordinary)} ordinary days: "
          f"median p_live {sorted(pl)[len(pl)//2]:.3f}, "
          f"index weight live at 1.0s photo {lw:.1f}%\n")

    print(f"{'date':11} {'replica%':>9} {'P(up)':>6} {'official%':>10} "
          f"{'call':>6} {'liveW%':>7}")
    hits = n = 0
    results = []
    for d in quirks:
        if d not in spx_hist:
            continue
        prev = index_days[index_days.index(d) - 1]
        dg = digest(d)
        pred, closes = {}, {}
        for t, po in dg["pred"].items():
            ref = dg["ref"].get(t) or prior_close(prices, t, d, index_days)
            if ref:
                pred[t] = po
                closes[t] = ref
        dist = pipeline.replica_distribution(pred, closes, timing=tm)
        est = pipeline.replica_estimate(pred, closes)
        official = (spx_hist[d][0] / spx_hist[prev][1] - 1) * 100
        ok = (dist["mean"] > 0) == (official > 0)
        hits += ok
        n += 1
        results.append({"date": d, "replica_pct": dist["mean"],
                        "p_up": dist["p_up"], "official_pct": official,
                        "hit": ok, "live_weight_pct": est["live_weight_pct"]})
        print(f"{d} {dist['mean']:>+8.3f}% {dist['p_up']:>6.2f} "
              f"{official:>+9.3f}% {'HIT' if ok else 'MISS':>6} "
              f"{est['live_weight_pct']:>6.1f}%")

    print(f"\nquirk days called by the auction replica: {hits}/{n}")
    print("paper (appendix replica.tex) states futures alone call 2 of 12 "
          "quirk days; that figure is NOT computed here and is not\n"
          "  directly comparable - it uses a different criterion. A\n"
          "  like-for-like futures baseline on these same 12 days is\n"
          "  still owed before claiming any improvement.")
    out = CACHE / "stage3_eval.json"
    out.write_text(json.dumps({"fit_days": ordinary, "results": results,
                               "hits": hits, "n": n}, indent=1))
    print(f"artifact: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
