from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import pytest

from scripts.generate_reports import generate_all_reports
from src.constants import SCENARIO_IDS


@pytest.mark.asyncio
async def test_generate_reports_creates_output_files(tmp_path: Path):
    pop_path = tmp_path / "pop"
    out_dir = tmp_path / "reports"

    await generate_all_reports(str(pop_path), str(out_dir), mock_llm=True)

    for sid in SCENARIO_IDS:
        assert (out_dir / f"{sid}_report.md").exists()
    assert (out_dir / "executive_summary.md").exists()


@pytest.mark.asyncio
async def test_generate_reports_handles_mock_mode(tmp_path: Path):
    pop_path = tmp_path / "pop"
    out_dir = tmp_path / "reports"

    await generate_all_reports(str(pop_path), str(out_dir), mock_llm=True)

    summary = (out_dir / "executive_summary.md").read_text()
    assert "mock_llm=True" in summary


@pytest.mark.asyncio
async def test_executive_summary_covers_all_scenarios(tmp_path: Path):
    pop_path = tmp_path / "pop"
    out_dir = tmp_path / "reports"

    await generate_all_reports(str(pop_path), str(out_dir), mock_llm=True)

    summary = (out_dir / "executive_summary.md").read_text()
    for sid in SCENARIO_IDS:
        assert sid in summary
