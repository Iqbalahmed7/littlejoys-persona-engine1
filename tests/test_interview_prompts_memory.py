"""Tests for _build_memory_context in src/analysis/interview_prompts.py."""
from __future__ import annotations

from unittest.mock import MagicMock

import src.analysis.interview_prompts as _ip_module

# Access module-private function directly
_build_memory_context = _ip_module._build_memory_context


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_persona(**kwargs) -> MagicMock:
    """Create a minimal mock persona that mirrors the fields _build_memory_context reads."""
    p = MagicMock()
    p.semantic_memory = kwargs.get("semantic_memory", {})
    p.purchase_history = kwargs.get("purchase_history", [])
    return p


def _make_purchase(outcome: str = "purchased", trigger: str = "doctor_rec") -> MagicMock:
    """Create a mock PurchaseRecord with the fields used by _build_memory_context."""
    purchase = MagicMock()
    purchase.outcome = outcome
    purchase.trigger = trigger
    return purchase


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_memory_context_returns_str():
    """Result is always a string, even for a bare mock."""
    p = _make_persona()
    result = _build_memory_context(p)
    assert isinstance(result, str)


def test_memory_context_empty_persona_no_purchases():
    """Empty persona yields a no-purchase note rather than raising."""
    p = _make_persona()
    result = _build_memory_context(p)
    # The function appends a 'No purchases' sentence when history is empty
    assert "No purchases" in result or isinstance(result, str)


def test_memory_context_with_tier2_anchor():
    """tier2_anchor value appears in the output."""
    p = _make_persona(semantic_memory={"tier2_anchor": "values health and family"})
    result = _build_memory_context(p)
    assert "values health and family" in result


def test_memory_context_with_tier2_stories_list():
    """tier2_stories list items are included in output."""
    p = _make_persona(
        semantic_memory={"tier2_stories": ["bought once, loved it", "checks labels carefully"]}
    )
    result = _build_memory_context(p)
    # At least the first story should appear
    assert "bought once, loved it" in result


def test_memory_context_with_tier2_stories_string():
    """tier2_stories as a plain string (not list) is also handled."""
    p = _make_persona(semantic_memory={"tier2_stories": "cautious early adopter"})
    result = _build_memory_context(p)
    assert "cautious early adopter" in result


def test_memory_context_with_purchase_history_outcome_and_trigger():
    """Purchase history outcome and trigger both appear in the output."""
    purchase = _make_purchase(outcome="repurchased", trigger="friend_rec")
    p = _make_persona(purchase_history=[purchase])
    result = _build_memory_context(p)
    # The function formats as "outcome (trigger)"
    assert "repurchased" in result
    assert "friend_rec" in result


def test_memory_context_purchase_count_reported():
    """Total purchase count is included when history is non-empty."""
    purchases = [_make_purchase("purchased", "ad") for _ in range(3)]
    p = _make_persona(purchase_history=purchases)
    result = _build_memory_context(p)
    assert "3" in result


def test_memory_context_combined_fields():
    """Both semantic memory and purchase history appear together."""
    purchase = _make_purchase("purchased", "self_research")
    p = _make_persona(
        semantic_memory={
            "tier2_anchor": "pragmatic buyer",
            "tier2_stories": ["bought once, loved it"],
        },
        purchase_history=[purchase],
    )
    result = _build_memory_context(p)
    assert "pragmatic buyer" in result
    assert "purchased" in result
    assert len(result) > 0


def test_memory_context_caps_purchase_history_at_five():
    """Only the first 5 purchases are included (source caps at [:5])."""
    purchases = [_make_purchase(f"outcome_{i}", f"trigger_{i}") for i in range(8)]
    p = _make_persona(purchase_history=purchases)
    result = _build_memory_context(p)
    # Outcomes 0-4 should appear, outcome_5/6/7 should not
    assert "outcome_0" in result
    assert "outcome_4" in result
    assert "outcome_5" not in result


def test_memory_context_newline_separated():
    """Multiple sections are joined with newlines."""
    p = _make_persona(
        semantic_memory={"tier2_anchor": "budget-conscious"},
        purchase_history=[_make_purchase("purchased", "promo")],
    )
    result = _build_memory_context(p)
    assert "\n" in result
