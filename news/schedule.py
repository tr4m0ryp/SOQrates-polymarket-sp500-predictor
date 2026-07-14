"""Group-B fetch routines: cadence per feed, checkpoints, triggers, budget.

Derived from the decisive-hour profile (news/timing.py): moves spread all
night with 31% in the 8:00-9:00 hour, so scheduled runs cluster late and
triggers cover the gaps between them.
"""

CHECKPOINTS_ET = ("02:30", "04:30", "07:00", "08:00", "08:35", "09:15")

FEED_CADENCE = {
    "alpaca_news_ws": "stream (buffer between runs; free key)",
    "truth_social": "poll 2 min 06:00-09:30 ET, 5 min overnight",
    "gdelt_sweep": "checkpoints only (rate limit >=5s/call)",
    "edgar_8k": "poll 16:00-18:30 ET prior evening (heavyweight earnings)",
    "bls_bea_endpoints": "one fetch at exactly 08:30:00 ET on release days",
    "prediction_odds": "poll 15 min; numeric delta check, no LLM",
}

TRIGGERS = {
    "gap_move": "|ES gap change| >= 0.15% within 15 min",
    "odds_delta": ">= 5 pts vs midnight baseline on watched markets",
    "wire_velocity": ">= 8 buffered relevant articles within 15 min",
}

MAX_TRIGGERED_RUNS = 6      # cap: 6 scheduled + <=6 triggered LLM calls/night
