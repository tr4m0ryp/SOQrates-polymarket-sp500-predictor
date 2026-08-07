"""Official-open ground truth: Yahoo ^GSPC cross-checked against stooq ^spx."""
import csv
import io
import urllib.request

from spx.data import yahoo

_STOOQ = "https://stooq.com/q/d/l/?s=%5Espx&i=d"


def stooq_daily() -> dict[str, tuple[float, float]]:
    req = urllib.request.Request(_STOOQ, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        text = r.read().decode()
    out = {}
    for row in csv.DictReader(io.StringIO(text)):
        try:
            out[row["Date"]] = (float(row["Open"]), float(row["Close"]))
        except (KeyError, ValueError):
            continue
    return out


def audit(days_back: int = 330, tol_pts: float = 0.75) -> list[dict]:
    """Days where the two sources disagree on the official open by > tol_pts."""
    ya = yahoo.daily_open_close("^GSPC", days_back)
    st = stooq_daily()
    bad = []
    for d in sorted(set(ya) & set(st)):
        diff = ya[d][0] - st[d][0]
        if abs(diff) > tol_pts:
            bad.append({"date": d, "yahoo_open": ya[d][0],
                        "stooq_open": st[d][0], "diff_pts": round(diff, 2)})
    return bad
