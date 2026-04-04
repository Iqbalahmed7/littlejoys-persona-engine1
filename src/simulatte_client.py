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


def _normalise_persona(p: dict) -> dict:
    """Add compatibility aliases so UI field expectations match API shape.

    The app_adapter returns:
      - top-level ``name``              → UI reads ``display_name``
      - ``demographics.age``            → UI reads ``demographics.parent_age``
      - ``demographics.employment_status`` → UI reads ``career.employment_status``

    We add the missing keys in-place so every consumer works without changes.
    """
    # 1. display_name alias
    if "display_name" not in p:
        p["display_name"] = p.get("name") or p.get("id", "")

    d = p.get("demographics", {})

    # 2. parent_age alias
    if "parent_age" not in d and "age" in d:
        d["parent_age"] = d["age"]

    # 3. career.employment_status alias
    if "career" not in p and "employment_status" in d:
        p["career"] = {"employment_status": d["employment_status"]}

    # 4. child_ages reconstruction — if the API omits it but provides
    #    youngest/oldest/num_children, reconstruct a plausible list so
    #    the Child Ages column and child-age-band metrics work correctly.
    if not d.get("child_ages"):
        youngest = d.get("youngest_child_age")
        oldest = d.get("oldest_child_age")
        num = d.get("num_children")
        if youngest is not None and oldest is not None and isinstance(num, int) and num >= 1:
            if num == 1:
                d["child_ages"] = [youngest]
            else:
                age_span = max(int(oldest) - int(youngest), 0)
                if age_span == 0:
                    d["child_ages"] = [int(youngest)] * num
                else:
                    step = age_span / max(num - 1, 1)
                    d["child_ages"] = [round(int(youngest) + step * i) for i in range(num)]

    return p


def _load_local_child_ages() -> dict[str, list[int]]:
    """Load a mapping of persona_id → child_ages from the local personas_generated.json.

    Used to backfill child age data that the API omits.
    Returns empty dict if file is not found or unreadable.
    """
    import json
    import pathlib

    candidates = [
        pathlib.Path(__file__).parent.parent / "data" / "population" / "personas_generated.json",
        pathlib.Path(__file__).parent.parent / "data" / "population" / "personas.json",
    ]
    for path in candidates:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            personas = data if isinstance(data, list) else list(data.values())
            result: dict[str, list[int]] = {}
            for p in personas:
                pid = str(p.get("id") or p.get("persona_id") or "")
                ages = p.get("demographics", {}).get("child_ages") or []
                if pid and ages:
                    result[pid] = ages
            return result
        except Exception:
            continue
    return {}


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
    # Normalise field names, then key by id
    result = {
        str(p.get("id") or p.get("persona_id") or i): _normalise_persona(p)
        for i, p in enumerate(personas)
    }

    # Backfill child_ages from local file when API returns empty lists.
    # The API adapter strips this field; local personas_generated.json has the truth.
    local_ages = _load_local_child_ages()
    if local_ages:
        for pid, persona in result.items():
            d = persona.get("demographics", {})
            if not d.get("child_ages"):
                if pid in local_ages:
                    d["child_ages"] = local_ages[pid]
                else:
                    # Try matching by display_name prefix (e.g. "Janaki-Nagpur-Mom-34")
                    display = persona.get("display_name", "")
                    for local_pid, ages in local_ages.items():
                        if local_pid.startswith(display.split("-")[0] + "-"):
                            d["child_ages"] = ages
                            break

    return result


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
