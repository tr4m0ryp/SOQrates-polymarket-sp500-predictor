"""Bulk headline gatherer for the LLM-layer historical replay.

For every strategy day, snapshot GDELT exactly as production would have at
the decision checkpoints. No hindsight: each snapshot's window ends at the
checkpoint. Cached per day under .cache/news_llm_replay/ and resumable.
"""
import datetime as dt
import json
import time

from config import CACHE, NY
from macro import releases
from news import gdelt

OUT_DIR = CACHE / "news_llm_replay"
CHECKPOINTS = {"04:00": 9.0, "07:00": 3.0, "08:35": 2.0}   # ET -> hours back
PAUSE = 20.0        # GDELT serves its rate-limit page as HTTP 200 with no
EMPTY_RETRIES = 2   # articles - so empty results are retried, not trusted


def _utc_str(date: str, et_hhmm: str, hours_back: float = 0.0) -> str:
    h, m = map(int, et_hhmm.split(":"))
    y, mo, d = map(int, date.split("-"))
    t = dt.datetime(y, mo, d, h, m, tzinfo=NY).astimezone(dt.timezone.utc)
    t -= dt.timedelta(hours=hours_back)
    return t.strftime("%Y%m%d%H%M%S")


def fetch_day(date: str) -> dict:
    date_obj = dt.date(*map(int, date.split("-")))
    day = {"date": date,
           "group_a_block": {
               "date": date,
               "releases_0830": releases.release_names(date_obj),
               "is_nfp_friday": releases.is_nfp_friday(date_obj),
               "prediction_baseline": [], "consensus": None},
           "checkpoints": {}}
    for cp, back in CHECKPOINTS.items():
        end = _utc_str(date, cp)
        start = _utc_str(date, cp, hours_back=back)
        heads, err = [], None
        for attempt in range(1 + EMPTY_RETRIES):
            time.sleep(PAUSE * (attempt + 1))
            try:
                heads = gdelt.query(gdelt.MARKET_QUERY, start=start, end=end,
                                    max_records=25)
                err = None
            except Exception as e:
                err = str(e)[:120]
                continue
            if heads:
                break                # non-empty = real answer
        if err is not None:
            day["checkpoints"][cp] = {"error": err}
            continue
        day["checkpoints"][cp] = {"headlines": [
            {"id": f"{cp}-h{i}", "ts": a["ts"], "source": a["domain"],
             "title": a["title"]} for i, a in enumerate(heads)]}
    return day


def fetch_all(dates: list[str], log=print) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for i, date in enumerate(dates):
        f = OUT_DIR / f"{date}.json"
        if f.exists():
            d = json.loads(f.read_text())
            if not any("error" in c for c in d["checkpoints"].values()):
                continue                     # complete - skip
        day = fetch_day(date)
        f.write_text(json.dumps(day))
        n = sum(len(c.get("headlines", [])) for c in day["checkpoints"].values())
        errs = sum(1 for c in day["checkpoints"].values() if "error" in c)
        log(f"[{i+1}/{len(dates)}] {date}: {n} headlines"
            + (f", {errs} checkpoint errors" if errs else ""))


def main():
    days = json.loads((CACHE / "strategy_days.json").read_text())
    dates = [d["date"] for d in days]
    half = len(dates) // 2
    # test half first: the walk-forward comparison unblocks sooner
    fetch_all(dates[half:] + dates[:half])


if __name__ == "__main__":
    main()
