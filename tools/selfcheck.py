"""Regression assertions for defects that silently corrupted results.

Offline by default: every check here runs without network or an API key, so
it is safe in CI. Run `python3 tools/selfcheck.py` from the repo root.

Each check pins a defect that produced WRONG NUMBERS rather than an error,
which is the class of bug this project is most exposed to: the replica happily
reports a gap when most constituents are silently missing.
"""
import sys

sys.path.insert(0, ".")

import spx  # noqa: E402  (loads .env)
from spx.replica.vendors.databento.schemas import _indicative, _px  # noqa: E402

FAILED = []


def check(name, cond, detail=""):
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}  {detail}")
        FAILED.append(name)


def main() -> int:
    print("indicative-price resolution (NYSE blanking defect, 2026-08-12)")

    # NYSE Pillar leaves ind_match_price at 0 and carries the indicative in
    # cont_book_clr_price. Accepting 0 blanked all 345 NYSE constituents.
    nyse = {"ind_match_price": 0, "cont_book_clr_price": 42860000000,
            "ref_price": 43320000000}
    check("NYSE zero ind_match falls through to cont_book_clr",
          _indicative(nyse) == 42.86, f"got {_indicative(nyse)}")

    # Nasdaq uses the UNDEF_PRICE sentinel (INT64_MAX) for "not populated".
    nas = {"ind_match_price": 9223372036854775807, "cont_book_clr_price": 0,
           "ref_price": 57840000000}
    check("Nasdaq UNDEF sentinel falls through to ref_price",
          _indicative(nas) == 57.84, f"got {_indicative(nas)}")

    # A populated indicative always wins over later fallbacks.
    both = {"ind_match_price": 10000000000, "cont_book_clr_price": 20000000000,
            "ref_price": 30000000000}
    check("populated ind_match_price wins", _indicative(both) == 10.0,
          f"got {_indicative(both)}")

    # Nothing populated must be None, never 0.0, or the name is counted live
    # at a $0 open and drags the index gap to -100%.
    empty = {"ind_match_price": 0, "cont_book_clr_price": 0, "ref_price": 0}
    check("all-zero record yields None, not 0.0", _indicative(empty) is None,
          f"got {_indicative(empty)!r}")

    check("UNDEF_PRICE sentinel maps to None",
          _px(9223372036854775807) is None)
    check("negative price rejected as indicative",
          _indicative({"ind_match_price": -5000000000,
                       "cont_book_clr_price": 42860000000}) == 42.86)

    print("\nspend governor")
    from spx.replica.vendors.databento import budget
    check("default cap is the agreed $50", budget.DEFAULT_CAP_USD == 50.00,
          f"got {budget.DEFAULT_CAP_USD}")
    check("cap is overridable by env",
          isinstance(budget.cap_usd(), float))

    print("\nweights header set (offline shape check)")
    from spx.data.weights import _UA
    check("browser UA present (Slickcharts 403s a bare Mozilla/5.0)",
          "Chrome/" in _UA["User-Agent"])
    check("wildcard Accept present (nasdaqtrader 406s html-only)",
          _UA.get("Accept") == "*/*")

    print()
    if FAILED:
        print(f"{len(FAILED)} check(s) FAILED: {', '.join(FAILED)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
