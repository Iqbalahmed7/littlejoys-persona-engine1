"""
Demographic distribution tables for Indian urban parents.

Sources: Census 2021, NFHS-5, D2C market reports.
All distributions are tier-conditional where applicable.

See ARCHITECTURE.md §5.3 for full specification.
Full implementation in PRD-001 (Codex).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd


class DistributionTables:
    """
    Real-world demographic distributions for Indian urban parents.

    Provides sampling methods that produce demographically realistic populations.
    All sampling is seeded for reproducibility.
    """

    def sample_demographics(self, n: int, seed: int) -> pd.DataFrame:
        """
        Sample n rows of demographic attributes from distribution tables.

        Args:
            n: Number of personas to sample.
            seed: Random seed for reproducibility.

        Returns:
            DataFrame with one row per persona, columns = demographic attribute names.

        Raises:
            ValueError: If n is out of valid range.
        """
        raise NotImplementedError("Full implementation in PRD-001")
