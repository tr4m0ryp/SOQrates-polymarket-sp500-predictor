# SPX Open Predictor

Predicts the official S&P 500 opening print (the 9:30 ET first index tick)
from overnight futures, regime-aware volatility, and opening-auction data,
and compares the model's probability against Polymarket's daily
"SPX Opens Up or Down" market. Stdlib-only Python; see `CLAUDE.md` for the
package map and commands.

```
python3 . backtest    # train/test metrics + quirk-day table
python3 . predict     # live P(up) now + Polymarket edge
```

## License

SPX Open Predictor is **source-available**, licensed under the
[PolyForm Noncommercial License 1.0.0](./LICENSE) — **not** an OSI
open-source license.

- **You may** use, modify, fork, and share SPX Open Predictor freely for any
  **noncommercial** purpose, as long as you keep the copyright and
  `Required Notice:` lines (see [`NOTICE`](./NOTICE)) and credit
  *"SPX Open Predictor by Keygraph, Inc."*
- **You may not** sell it, bundle it into a paid product, or run it as a
  paid/hosted service **without a commercial license**.

Copyright (c) 2026 Keygraph, Inc. Commercial licensing enquiries: see
[`NOTICE`](./NOTICE).
