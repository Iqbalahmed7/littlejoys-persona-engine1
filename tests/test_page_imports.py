"""Smoke tests: modules import without error."""
from __future__ import annotations

import importlib

import pytest


@pytest.mark.parametrize("module_path", [
    "app.components.system_voice",
    "app.utils.phase_state",
    "app.utils.probe_orchestrator",
])
def test_module_imports_cleanly(module_path: str) -> None:
    """Module can be imported without raising any exception."""
    # importlib.import_module returns the module object on success;
    # any ImportError or AttributeError will fail the test naturally.
    mod = importlib.import_module(module_path)
    assert mod is not None
