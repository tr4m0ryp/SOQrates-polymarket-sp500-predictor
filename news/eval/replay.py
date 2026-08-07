"""Historical replay eval: real archived headlines -> Group-B classifier.

For each labeled event day, fetch the GDELT headline snapshot ending at the
first checkpoint after the decisive move (what production would have seen),
run the real Group-B prompt, and score the LLM's direction against the
decisive move's actual sign. This is the end-to-end test of the news layer
on the days that historically cost money.
"""
import datetime as dt
import json
import time

from config import CACHE, NY
from macro import releases
from news.eval import timing
from news.llm import groupb, prompt, runner as llm
from news.sources import gdelt

CHECKPOINT_AFTER = {1: "02:30", 2: "02:30", 3: "04:30", 4: "04:30",
                    5: "07:00", 6: "07:00", 7: "07:00", 8: "08:00",
                    9: "08:35"}


def _utc(date: str, et_hhmm: str) -> str:
    h, m = map(int, et_hhmm.split(":"))
    y, mo, d = map(int, date.split("-"))
    t = dt.datetime(y, mo, d, h, m, tzinfo=NY).astimezone(dt.timezone.utc)
    return t.strftime("%Y%m%d%H%M%S")


def replay_day(row: dict, label: str | None = None,
               pause: float = 6.0) -> dict | None:
    """One labeled day through GDELT + LLM. Returns scored result."""
    gaps = row["es"]
    shock_h, delta = groupb.last_shock(gaps)
    if shock_h is None:
        shock_h, _ = timing.decisive_hour(gaps)
        delta = gaps[shock_h] - gaps.get(shock_h - 1, 0.0)
    checkpoint = CHECKPOINT_AFTER.get(shock_h, "08:35")
    end = _utc(row["date"], checkpoint)
    time.sleep(pause)
    try:
        heads = gdelt.query(gdelt.MARKET_QUERY,
                            start=str(int(end) - 40000), end=end,
                            max_records=25)
    except Exception as e:
        return {"date": row["date"], "error": f"gdelt: {e}"}
    date_obj = dt.date(*map(int, row["date"].split("-")))
    payload = {
        "group_a_block": {
            "date": row["date"],
            "releases_0830": releases.release_names(date_obj),
            "is_nfp_friday": releases.is_nfp_friday(date_obj),
            "prediction_baseline": [], "consensus": None,
        },
        "headlines_since_last_run": [
            {"id": f"h{i}", "ts": a["ts"], "source": a["domain"],
             "title": a["title"]} for i, a in enumerate(heads)],
        "odds_deltas": {}, "seen_ids": [],
    }
    try:
        out = llm.run(prompt.GROUP_B_PROMPT, payload, prompt.validate_b)
    except llm.LlmError as e:
        return {"date": row["date"], "error": str(e)[:100]}
    want = 1 if delta > 0 else -1
    got = out["direction"]
    verdict = ("CORRECT" if got * want > 0 and abs(got) >= 0.3 else
               "weak-right" if got * want > 0 else
               "missed(0)" if got == 0 else "WRONG-SIGN")
    return {"date": row["date"], "checkpoint": checkpoint,
            "n_headlines": len(heads), "move": round(delta, 2),
            "llm_direction": got, "confidence": out["confidence"],
            "event_type": out["event_type"], "shock": out["shock"],
            "verdict": verdict, "rationale": out["rationale"],
            "label": label or ""}


def replay_labeled(rows: list[dict]) -> list[dict]:
    labels = json.loads((CACHE.parent / "news" / "event_labels.json").read_text())
    by_date = {r["date"]: r for r in rows}
    out = []
    for date, label in labels.items():
        if date.startswith("_") or date not in by_date:
            continue
        res = replay_day(by_date[date], label)
        if res:
            out.append(res)
            print(f"{res['date']} {res.get('verdict', res.get('error','?')):12}"
                  f" dir {res.get('llm_direction', '-'):>5} "
                  f"conf {res.get('confidence', '-'):>4} "
                  f"({res.get('n_headlines', 0)} headlines) "
                  f"| {res.get('rationale', '')[:80]}")
    (CACHE / "news_replay.json").write_text(json.dumps(out, indent=1))
    return out
