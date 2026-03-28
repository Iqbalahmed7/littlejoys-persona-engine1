"""Create required data directories for the dashboard and analysis outputs."""

from __future__ import annotations

from pathlib import Path

DIRS = [
    "data/population",
    "data/results",
    "data/results/reports",
    "data/scraped",
    "data/distributions",
]


def setup() -> None:
    """Create required data directories."""

    for d in DIRS:
        Path(d).mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    setup()
