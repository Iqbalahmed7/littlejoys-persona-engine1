from unittest.mock import MagicMock, patch

import pytest

from app.components.quadrant_grid import render_quadrant_grid
from src.analysis.intervention_engine import Intervention, InterventionQuadrant


@pytest.fixture
def mock_quadrant():
    i_gt = Intervention(
        id="gt", name="Gen Temp", description="D",
        scope="general", temporality="temporal",
        target_cohort_id=None,
        expected_mechanism="M", parameter_modifications={}
    )
    i_gn = Intervention(
        id="gn", name="Gen Non", description="D",
        scope="general", temporality="non_temporal",
        target_cohort_id=None,
        expected_mechanism="M", parameter_modifications={}
    )
    i_ct = Intervention(
        id="ct", name="Coh Temp", description="D",
        scope="cohort_specific", temporality="temporal",
        target_cohort_id="c1",
        expected_mechanism="M", parameter_modifications={}
    )
    i_cn = Intervention(
        id="cn", name="Coh Non", description="D",
        scope="cohort_specific", temporality="non_temporal",
        target_cohort_id="c2",
        expected_mechanism="M", parameter_modifications={}
    )
    return InterventionQuadrant(
        problem_id="prob1",
        quadrants={
            "general_temporal": [i_gt],
            "general_non_temporal": [i_gn],
            "cohort_temporal": [i_ct],
            "cohort_non_temporal": [i_cn]
        }
    )

def test_render_quadrant_grid_smoke(mock_quadrant):
    with patch("streamlit.markdown") as mock_markdown, \
         patch("streamlit.columns") as mock_columns, \
         patch("streamlit.caption") as mock_caption, \
         patch("streamlit.container") as mock_container:

        # Setup mock for columns to return enough mocks for destructuring
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_columns.side_effect = [[mock_col1, mock_col2], [mock_col1, mock_col2]]

        # Container mock to act as a context manager
        mock_container.return_value.__enter__ = MagicMock()
        mock_container.return_value.__exit__ = MagicMock()

        render_quadrant_grid(mock_quadrant)

        # Basic check to ensure streamlit functions were called
        assert mock_markdown.called
        assert mock_columns.called
        assert mock_caption.called

        # Verify specific content was attempted (e.g. Row headers)
        calls = [call.args[0] for call in mock_markdown.call_args_list]
        assert "### Temporal interventions" in calls
        assert "### Non-temporal interventions" in calls
        assert "**Gen Temp**" in calls
        assert "**Gen Non**" in calls
        assert "**Coh Temp**" in calls
        assert "**Coh Non**" in calls

def test_render_quadrant_grid_empty():
    empty_quadrant = InterventionQuadrant(
        problem_id="empty",
        quadrants={
            "general_temporal": [],
            "general_non_temporal": [],
            "cohort_temporal": [],
            "cohort_non_temporal": []
        }
    )
    with patch("streamlit.markdown"), \
         patch("streamlit.columns") as mock_columns, \
         patch("streamlit.caption") as mock_caption:

        mock_columns.return_value = [MagicMock(), MagicMock()]

        render_quadrant_grid(empty_quadrant)

        # Check total count message
        mock_caption.assert_any_call("0 interventions across 4 quadrants")

@pytest.mark.parametrize("name", ["Int A", "Int B", "Int C", "Int D", "Special #1", "Edge Case \""])
def test_render_quadrant_grid_name_rendering(name):
    from unittest.mock import MagicMock, patch
    i = Intervention(
        id="i", name=name, description="D",
        scope="general", temporality="temporal",
        target_cohort_id=None,
        expected_mechanism="M", parameter_modifications={}
    )
    quadrant = InterventionQuadrant(
        problem_id="p",
        quadrants={"general_temporal": [i]}
    )
    with patch("streamlit.markdown") as mock_markdown, \
         patch("streamlit.columns") as mock_columns, \
         patch("streamlit.container") as mock_container:

        mock_columns.return_value = [MagicMock(), MagicMock()]
        mock_container.return_value.__enter__ = MagicMock()

        render_quadrant_grid(quadrant)

        mock_markdown.assert_any_call(f"**{name}**")
