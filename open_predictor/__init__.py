"""SPX official-open predictor - all source packages.

Loads `.env` at the repo root into the environment on import, so API keys
reach every entry point regardless of how the shell was started (login,
non-interactive, or a subagent shell that sources no profile). Real
environment variables always win: `.env` only fills what is unset.
"""
import os
from pathlib import Path


def _load_dotenv() -> None:
    path = Path(__file__).resolve().parents[1] / ".env"
    try:
        text = path.read_text()
    except OSError:
        return
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


_load_dotenv()
