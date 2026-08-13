# Open Questions: What the Repo Alone Cannot Answer

These gaps were found while writing this pack by reading every file in the
tree. Each is something a fresh session cannot resolve from the repo: the
answer lives in project memory, an external account, or a decision not yet
made. Ask the project owner, or treat the item as unverified until closed.
When one is resolved, move the answer into the relevant numbered page and
delete the entry here.

1. Whether the system is currently trading live with real money, and any live P&L since the paper's 58-day test window, is not recorded in the repo.
2. Whether the Polymarket market still operates at the volumes cited (it had thinned to $30-48k/day by July 2026) cannot be determined from the repo.
3. CLAUDE.md's package map lists directories as data/, model/, pm/ etc., but the code actually lives under spx/ (e.g. spx/model/); the repo does not say whether the map predates a move.
4. No CLI command launches the live 9:28-9:30 stage-3 path: the live pieces exist (spx/replica/vendors/databento/live.py stream_imbalance, spx/replica/vendors/stitch/feeds.py Massive websocket) but nothing in spx/cli wires them into a runnable loop, so how live stage-3 is meant to be started cannot be determined from the repo.
5. The live predict command does not invoke the news layer; whether news-voice fusion is planned for cmd_predict or intentionally kept offline-only is not stated in the code (the roadmap lives in project memory, not the repo).
6. The repo CLAUDE.md says ground-truth disagreement days are excluded from fits, but no code in spx/backtest/ calls ground_truth.audit(); whether exclusion happens manually outside the repo or is simply not yet wired cannot be determined from the code.
7. ALPACA_API_KEY / ALPACA_API_SECRET are required by spx/data/alpaca.py but are absent from the env-keys list in the repo CLAUDE.md, and no CLI command or module currently imports spx/data/alpaca.py, so its intended integration point is not visible in the repo.
8. Provenance of the frozen constants A0 = 0.0092 and K_DEFAULT = 0.767: the fitting window and procedure are not in the repo (CLAUDE.md says model background lives in project memory, spx-open-predictor-roadmap.md).
9. How QUIRK_DAYS were identified: the list in spx/config.py is hand-maintained; no script in the repo reproduces the selection.
10. Why CONF_COMMIT is 0.65 and SWITCH_HOUR is 5: core.py's comment gives the rationale (v1.3 sharper early, v1.2 better calibrated late) but the supporting numbers are not in the repo.
11. ~~Whether the Databento account is entitled to XNYS.PILLAR~~ **RESOLVED 2026-08-12:** yes. `databento-status` reports 29 datasets with XNAS.ITCH and XNYS.PILLAR both visible, and a real 29-day backfill pulled NYSE imbalance records on every day. See `05-replica.md`.
12. The exact Databento cross flag for the opening print: cross_print_map uses the earliest priced trade in a 9:29:55-9:34 window as a heuristic pending the first keyed pull
13. Actual LSEG auction FID names: parse.py's FID_MAP is candidates only, untested until DSS credentials exist
14. Whether Webull request signing uses HMAC-SHA256 (current docs) or HMAC-SHA1 (SDK default); unconfirmed against a live key, as is the NOII response field map
15. ~~Whether the print-delay model has been fitted on real timestamps~~ **RESOLVED 2026-08-12:** it had not been, until this run. Fitted on 17 ordinary days of real Databento cross prints. Measured reality (29 days, n=14,439 prints): median 1.026s, 46.2% within 1.0s, 92.6% within 2.0s, against venue priors of 0.97 Nasdaq / 0.15 NYSE. An earlier figure of "96% within 5s, median 0.93s" circulated briefly and is WRONG: it was computed before the opening-cross defect was found, from pre-open odd lots rather than auction prints. One day of data caps Laplace-smoothed `p_live` at 0.75, so a stable fit needs roughly 10+ days. See `05-replica.md`.
16. Which LLM provider and model run in production: LLM_BASE_URL/LLM_MODEL are env-configured and no chosen values or bench results are recorded in the repo.
17. Three of the five STREAM_FEEDS (truth_social, edgar_8k, release_endpoints) and the prefetch slots nowcast_cpi/consensus/earnings_after_close have no implementation or data source in the repo.
18. No scheduler or daemon in the repo executes the CHECKPOINTS_ET cadence in spx/news/ops/schedule.py; how the live nightly loop is launched is not determinable from the code.
19. The fee model in spx/strategy/engine/execution.py cites '2026-07-18 microstructure research' for Fee Structure V2 (rate 0.04 since 2026-03-30), but that research document is not in the repo, so the source and whether the fee schedule is still current cannot be verified here.
20. The bootstrap runner (spx/strategy/analysis/bootstrap.py) has a main() but no CLI subcommand in spx/cli/__init__.py; whether that is intentional or an omission is not stated anywhere in the repo.
21. spx/pm/history.py hardcodes SERIES_ID 10945 for the Polymarket series; the repo does not record how that id was obtained or how to re-derive it if Polymarket changes it.
22. The ground-truth exclusion rule is a convention, not code: spx/backtest/dataset.py has no filter for Yahoo-vs-stooq disagreement days, and the repo does not show whether any day has ever needed manual exclusion (the audit message implies full agreement so far, but .cache/ is empty in this clone).
23. The docstrings in baselines.py and reality_check.py give the invocation `python3 -m backtest.<module>`, which does not resolve (no top-level backtest package); the working form is `python3 -m spx.backtest.<module>`. Whether the stale form predates a package rename cannot be confirmed from the repo.
24. reality_check.py cites its candidate provenance as workflow run wf_89eb270d in session 380c3a0d; that record is not in the repo, so the 15-candidate list cannot be independently verified here.
25. baselines.py and reality_check.py depend on .cache/pm_history/ (populated by `python3 . pm-history`); how many days of Polymarket history are actually available, and thus the exact crowd-row and 58-day-test counts, cannot be determined from the repo alone.
26. The `quirks` command exists in spx/cli/__init__.py but is absent from the CLAUDE.md command list; unclear if that omission is intentional.
27. CLAUDE.md mentions MASSIVE_API_KEY for a live NYSE imbalance websocket leg, but no CLI command references it, so which command (if any) will consume it cannot be determined from spx/cli/.
28. The manifest notes say PDF versions of reliability_diagram and strategy_bankroll_50 were regenerated into research/plots/, but no .pdf files exist anywhere under research/ in the current tree; whether they were deleted deliberately or lost is not recorded in the repo.
29. Five of eight manifest figures have producing_script: null (producer scripts were session scratch); the repo cannot say whether anyone intends to rebuild those scripts so the headline accuracy figures become regenerable.
30. The Overleaf mirror state (slug soqrates, project id) lives outside the repo in ~/projects/research/overleaf-mirror/manifest.tsv and ~/.claude/CLAUDE.md; a teammate without that home directory cannot discover the sync workflow from the repo alone.
31. The .venv-wrds virtualenv referenced by CLAUDE.md and tools/wrds_probe.py does not exist in this checkout, and the repo does not record how to create it (no requirements file or setup script for it); presumably `python3 -m venv .venv-wrds && .venv-wrds/bin/pip install wrds`, but that is not written down anywhere.
32. CLAUDE.md points to project memory (spx-open-predictor-roadmap.md) for model background and validated numbers; that file is not in the repo, so its contents cannot be verified from here.
