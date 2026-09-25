"""Constants and cache paths shared across the package."""
from pathlib import Path
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache"
CACHE.mkdir(exist_ok=True)

A0 = 0.0092          # intercept of official-gap regression (%)
K_DEFAULT = 0.767    # pooled futures->official attenuation
EWMA_LAMBDA = 0.94   # decay for overnight gap^2 EWMA
SMALL_GAP = 0.25     # |gap| %-threshold below which small-gap k applies
SMALL_GAP_HOURS = (0, 1, 2, 3, 4)
NFP_SIGMA_MULT = 1.3     # fallback release-morning widening (used when too few samples to fit)
RELEASE_MULT_BOUNDS = (1.0, 2.5)   # clamp for the fitted release multiplier
CONF_COMMIT = 0.65       # below this confidence = coin-flip / no-bet
LOOKBACK_DAYS = 720      # hourly futures history window (Yahoo 60m cap ~730d)
DATASET_DAYS = 480       # trading days kept in the backtest dataset

QUIRK_DAYS = [           # ES held direction, official printed opposite/tiny
    "2025-09-12", "2025-09-17", "2025-11-06", "2025-12-03",
    "2026-01-29", "2026-02-24", "2026-02-26", "2026-03-10",
    "2026-04-09", "2026-06-01", "2026-06-22", "2026-07-10",
]
