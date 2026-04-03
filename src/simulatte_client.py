"""
HTTP client for the Simulatte Persona Generator API.

Replaces the local sys.path hack that imported from the sibling
'Persona Generator' project directory. All persona data now flows
through the deployed REST API.

Configuration (via environment variables or Streamlit secrets):
    SIMULATTE_API_URL    — base URL of the Persona Generator service
                           default: https://simulatte-persona-generator.onrender.com
    SIMULATTE_COHORT_ID  — which cohort to load on startup
                           default: littlejoys-v1  (the committed seed cohort)
"""
from __future__ import annotations

import os
from typing import Any

import httpx

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_DEFAULT_API_URL = "https://simulatte-persona-generator.onrender.com"
_DEFAULT_COHORT_ID = "littlejoys-v1"

# Pull from env (set in Streamlit Cloud Secrets or .env.local)
SIMULATTE_API_URL: str = os.environ.get("SIMULATTE_API_URL", _DEFAULT_API_URL).rstrip("/")
SIMULATTE_COHORT_ID: str = os.environ.get("SIMULATTE_COHORT_ID", _DEFAULT_COHORT_ID)

# Generous timeout — Render free tier cold-starts can take 30 s
_TIMEOUT = httpx.Timeout(60.0, connect=15.0)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def health_check() -> dict[str, Any]:
    """Return the API health payload, or raise on failure."""
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.get(f"{SIMULATTE_API_URL}/health")
        resp.raise_for_status()
        return resp.json()


def list_cohorts() -> list[str]:
    """Return all cohort IDs available on the Persona Generator service."""
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.get(f"{SIMULATTE_API_URL}/cohorts")
        resp.raise_for_status()
        return resp.json().get("cohort_ids", [])


def load_personas(cohort_id: str | None = None) -> dict[str, dict]:
    """
    Fetch personas from the Persona Generator API and return them as a
    ``{persona_id: display_dict}`` mapping — the same format that
    ``load_all_personas()`` in streamlit_app.py expects.

    Uses the ``GET /cohort/{cohort_id}/personas`` endpoint which runs
    the LittleJoys app_adapter conversion server-side.

    Args:
        cohort_id: cohort to load; defaults to ``SIMULATTE_COHORT_ID``.

    Returns:
        Dict mapping persona_id → display dict, or empty dict on failure.

    Raises:
        httpx.HTTPStatusError: if the API returns a 4xx/5xx response.
        httpx.TimeoutException: if the request exceeds the timeout.
    """
    cid = cohort_id or SIMULATTE_COHORT_ID
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.get(f"{SIMULATTE_API_URL}/cohort/{cid}/personas")
        resp.raise_for_status()
        data = resp.json()

    personas: list[dict] = data.get("personas", [])
    # Key by persona_id (preferred) or id (legacy field name)
    return {
        str(p.get("persona_id") or p.get("id") or i): p
        for i, p in enumerate(personas)
    }


def get_cohort_raw(cohort_id: str | None = None) -> dict[str, Any]:
    """
    Fetch the raw CohortEnvelope JSON for a cohort.

    Returns the full ``cohort`` dict from ``GET /cohort/{cohort_id}``.
    """
    cid = cohort_id or SIMULATTE_COHORT_ID
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.get(f"{SIMULATTE_API_URL}/cohort/{cid}")
        resp.raise_for_status()
        return resp.json()
