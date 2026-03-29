"""Shared Anthropic API key resolution for Streamlit pages."""

from __future__ import annotations

import streamlit as st

from src.config import get_config


def resolve_api_key() -> str:
    """Read Anthropic API key from Streamlit secrets (cloud) or .env.local (local).

    Returns the key string, or empty string if none found / placeholder only.
    """

    try:
        if hasattr(st, "secrets") and "ANTHROPIC_API_KEY" in st.secrets:
            return str(st.secrets["ANTHROPIC_API_KEY"]).strip()
    except Exception:
        pass
    key = get_config().anthropic_api_key.strip()
    if not key or key == "sk-ant-REPLACE_ME":
        return ""
    return key


def has_api_key() -> bool:
    """Return True if a non-placeholder API key is available."""

    key = resolve_api_key()
    return bool(key) and not key.startswith("sk-ant-REPLACE")

