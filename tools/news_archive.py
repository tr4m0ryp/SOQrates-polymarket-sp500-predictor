"""Build the frozen, timestamped overnight news archive for the replay.

One file per trading day holding every headline GDELT indexed between the
prior close and the open, each with its own `seendate`. The replay serves a
checkpoint by filtering on that timestamp, so any granularity is available
after the fact and no query has to be repeated.

Why slices rather than one query per day: the DOC API caps a result set at 250
and sorts newest-first, so a query with real volume silently loses its early
hours. Measured 2026-07-10, the broad production query returned 250 articles
covering only the last 2 hours of a 16.5-hour window; the phrase-tight query
used here runs about 62 articles/hour, so 2-hour slices stay under the cap and
coverage is complete.

Resumable by design: a day already on disk is skipped, so a 6-hour run can be
interrupted and restarted without losing work or refetching.

    python3 tools/news_archive.py                 # all Polymarket days
    python3 tools/news_archive.py --days 5        # smoke test on 5 days
"""
import argparse
import datetime as dt
import glob
import json
import os
import sys
import time
from zoneinfo import ZoneInfo

sys.path.insert(0, ".")

import spx  # noqa: E402  (loads .env)
from spx.config import CACHE  # noqa: E402
from spx.news.sources import gdelt  # noqa: E402
from spx.pm.history import HIST_DIR  # noqa: E402

NY = ZoneInfo("America/New_York")
OUT = CACHE / "news_archive"

# Phrase-anchored: every term is a multi-word phrase or an unambiguous market
# token, which keeps the volume low enough that 2-hour slices do not truncate.
# The production query ("strikes", "market", "fed") matches labour disputes and
# consumer-goods markets, which is why it returned photo-scanner articles.
QUERY = ('("federal reserve" OR "interest rate" OR "interest rates" OR '
         '"inflation data" OR "stock futures" OR "wall street" OR '
         '"treasury yield" OR "jobs report" OR "consumer price" OR '
         '"s&p 500" OR "nasdaq futures" OR tariffs)')

# 20:00 rather than 16:00: the 16:00-20:00 block is post-close US evening with
# little market-moving flow, and each slice costs ~25s of GDELT latency. This
# trims 2 slices/day (about 1.5h across the window) for very little coverage.
WINDOW_START_ET = dt.time(20, 0)     # prior evening, around the Asia open
WINDOW_END_ET = dt.time(9, 30)       # the open we are predicting
SLICE_HOURS = 2
PAUSE = 8.0                          # measured: throttling is erratic, and
                                     # request latency (17-34s) dominates anyway
EMPTY_RETRIES = 2                    # a rate-limit page is HTTP 200 with 0 hits
THROTTLE_BACKOFF = 90.0              # on an explicit 429, wait properly


def utc(day: str, t: dt.time, offset_days: int = 0) -> dt.datetime:
    y, m, d = (int(x) for x in day.split("-"))
    local = dt.datetime(y, m, d, t.hour, t.minute, tzinfo=NY) \
        + dt.timedelta(days=offset_days)
    return local.astimezone(dt.timezone.utc)


def fetch_day(day: str) -> dict:
    start = utc(day, WINDOW_START_ET, -1)
    end = utc(day, WINDOW_END_ET, 0)
    arts, slices, slice_log = {}, 0, []
    cur = start
    while cur < end:
        nxt = min(cur + dt.timedelta(hours=SLICE_HOURS), end)
        # A throttled response and a genuinely quiet slice look identical:
        # both are HTTP 200 with zero articles. Retry every empty result, and
        # record which slices never returned data so the fidelity report can
        # separate "nothing happened" from "we never found out".
        got, status = [], "ok"
        for attempt in range(EMPTY_RETRIES + 1):
            try:
                got = gdelt.query(QUERY,
                                  cur.strftime("%Y%m%d%H%M%S"),
                                  nxt.strftime("%Y%m%d%H%M%S"),
                                  max_records=250, sort="datedesc")
            except Exception as e:                      # noqa: BLE001
                status = "throttled" if "429" in str(e) else "error"
                time.sleep(THROTTLE_BACKOFF if status == "throttled" else PAUSE)
                continue
            if got:
                status = "ok"
                break
            status = "empty_unverified"
            if attempt < EMPTY_RETRIES:
                time.sleep(PAUSE * 2)
        slice_log.append({"start": cur.isoformat(), "status": status,
                          "n": len(got)})
        for a in got:
            if a.get("ts") and a.get("title"):
                arts[a["url"]] = a          # url dedupes across slice edges
        slices += 1
        if len(got) >= 250:
            arts.setdefault("_truncated", True)
        cur = nxt
        time.sleep(PAUSE)
    rows = sorted((a for k, a in arts.items() if k != "_truncated"),
                  key=lambda x: x["ts"])
    bad = [s2 for s2 in slice_log if s2["status"] != "ok"]
    return {"date": day, "query": QUERY, "slices": slices,
            "window_utc": [start.isoformat(), end.isoformat()],
            "truncated_slice": "_truncated" in arts,
            "slice_log": slice_log, "unverified_slices": len(bad),
            "complete": not bad,
            "n": len(rows), "articles": rows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=0, help="limit, for smoke tests")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    days = sorted(os.path.splitext(os.path.basename(p))[0]
                  for p in glob.glob(str(HIST_DIR) + "/*.json"))
    if args.days:
        days = days[-args.days:]

    todo = [d for d in days if not (OUT / f"{d}.json").exists()]
    print(f"{len(days)} days in window, {len(days)-len(todo)} already archived, "
          f"{len(todo)} to fetch", flush=True)
    # GDELT's own response time (measured 17-34s) dominates, not the pause.
    # Budget 25s latency + PAUSE per slice, or the estimate reads far too low.
    window_h = ((dt.datetime.combine(dt.date(2000, 1, 2), WINDOW_END_ET)
                 - dt.datetime.combine(dt.date(2000, 1, 1), WINDOW_START_ET))
                .total_seconds() / 3600)
    slices_per_day = -(-window_h // SLICE_HOURS)
    est = len(todo) * slices_per_day * (25.0 + PAUSE) / 3600
    print(f"{slices_per_day:.0f} slices/day over a {window_h:.1f}h window; "
          f"estimated wall clock: {est:.1f}h", flush=True)
    print("resumable: completed days are skipped on restart\n", flush=True)

    t0 = time.time()
    for i, day in enumerate(todo, 1):
        rec = fetch_day(day)
        (OUT / f"{day}.json").write_text(json.dumps(rec))
        el = time.time() - t0
        rate = el / i
        print(f"[{i}/{len(todo)}] {day}  {rec['n']:>4} articles  "
              f"{rec['slices']} slices"
              + ("  TRUNCATED" if rec["truncated_slice"] else "")
              + (f"  UNVERIFIED:{rec['unverified_slices']}"
                 if rec["unverified_slices"] else "")
              + f"  (eta {(len(todo)-i)*rate/3600:.1f}h)", flush=True)
    print(f"\ndone: {len(todo)} days in {(time.time()-t0)/3600:.2f}h")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
