"""Unit tests for pure helper logic inside Streamlit page modules."""

from __future__ import annotations

import importlib
import sys
from types import ModuleType, SimpleNamespace
from typing import Any

from src.constants import DEFAULT_SEED, SCENARIO_IDS
from src.simulation.static import StaticSimulationResult


class _SessionState(dict[str, Any]):
    def __getattr__(self, name: str) -> Any:
        if name in self:
            return self[name]
        raise AttributeError(name)

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


class _NullContext:
    def __enter__(self) -> _NullContext:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        del exc_type, exc, tb
        return False


class _Column:
    def __enter__(self) -> _Column:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        del exc_type, exc, tb
        return False

    def metric(self, *args: object, **kwargs: object) -> None:
        del args, kwargs


class _SidebarContext:
    def __init__(self, streamlit_module: _FakeStreamlit) -> None:
        self._streamlit_module = streamlit_module

    def __enter__(self) -> _FakeStreamlit:
        return self._streamlit_module

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        del exc_type, exc, tb
        return False


class _FakeStreamlit(ModuleType):
    def __init__(
        self,
        *,
        session_state: _SessionState | None = None,
        select_values: dict[str, Any] | None = None,
        text_inputs: dict[str, str] | None = None,
        toggles: dict[str, bool] | None = None,
        buttons: dict[str, bool] | None = None,
        chat_input_value: str | None = None,
    ) -> None:
        super().__init__("streamlit")
        self.session_state = session_state or _SessionState()
        self._select_values = select_values or {}
        self._text_inputs = text_inputs or {}
        self._toggles = toggles or {}
        self._buttons = buttons or {}
        self._chat_input_value = chat_input_value
        self.sidebar = _SidebarContext(self)

    def cache_resource(self, show_spinner: bool = False):  # type: ignore[no-untyped-def]
        del show_spinner

        def decorator(func):  # type: ignore[no-untyped-def]
            return func

        return decorator

    def cache_data(self, show_spinner: bool = False):  # type: ignore[no-untyped-def]
        del show_spinner

        def decorator(func):  # type: ignore[no-untyped-def]
            return func

        return decorator

    def set_page_config(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def title(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def header(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def caption(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def subheader(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def warning(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def success(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def error(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def info(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def markdown(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def write(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def json(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def plotly_chart(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def metric(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def divider(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def progress(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def download_button(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def spinner(self, *args: object, **kwargs: object) -> _NullContext:
        del args, kwargs
        return _NullContext()

    def expander(self, *args: object, **kwargs: object) -> _NullContext:
        del args, kwargs
        return _NullContext()

    def chat_message(self, *args: object, **kwargs: object) -> _NullContext:
        del args, kwargs
        return _NullContext()

    def columns(self, n: int) -> list[_Column]:
        return [_Column() for _ in range(n)]

    def stop(self) -> None:
        return None

    def rerun(self) -> None:
        return None

    def selectbox(self, label: str, options: Any, **kwargs: object) -> Any:
        key = kwargs.get("key")
        if isinstance(key, str) and key in self._select_values:
            return self._select_values[key]
        if label in self._select_values:
            return self._select_values[label]
        try:
            return next(iter(options))
        except Exception:
            return None

    def radio(self, label: str, options: Any = None, **kwargs: object) -> Any:
        del kwargs
        if options:
            return options[0]
        return None

    def toggle(self, label: str, value: bool = False, **kwargs: object) -> bool:
        del kwargs
        return self._toggles.get(label, value)

    def text_input(self, label: str, value: str = "", **kwargs: object) -> str:
        del kwargs
        return self._text_inputs.get(label, value)

    def button(self, label: str, **kwargs: object) -> bool:
        del kwargs
        return self._buttons.get(label, False)

    def slider(  # type: ignore[no-untyped-def]
        self,
        label: str,
        min_value: Any = None,
        max_value: Any = None,
        value: Any = None,
        step: Any = None,
        **kwargs: object,
    ) -> Any:
        del label, min_value, max_value, step, kwargs
        return value

    def chat_input(self, *args: object, **kwargs: object) -> str | None:
        del args, kwargs
        return self._chat_input_value


def _import_page_module(
    monkeypatch,
    module_name: str,
    fake_streamlit: _FakeStreamlit,
) -> Any:
    sys.modules.pop(module_name, None)
    monkeypatch.setitem(sys.modules, "streamlit", fake_streamlit)
    return importlib.import_module(module_name)


def _fake_population() -> Any:
    persona = SimpleNamespace(
        id="persona-1",
        tier="statistical",
        demographics=SimpleNamespace(city_name="Mumbai", household_income_lpa=12.0),
        career=SimpleNamespace(employment_status="full_time"),
        to_flat_dict=lambda: {
            "city_tier": "Tier1",
            "income_bracket": "middle_income",
            "budget_consciousness": 0.42,
            "health_anxiety": 0.63,
        },
    )

    class _Population:
        def __init__(self) -> None:
            self.tier1_personas = [persona]
            self.tier2_personas = [persona]
            self._lookup = {persona.id: persona}

        @property
        def personas(self) -> list[Any]:
            return self.tier1_personas

        def get_persona(self, persona_id: str) -> Any:
            return self._lookup[persona_id]

        def save(self, path: Any) -> None:
            del path

    return _Population()


def _import_results_page(monkeypatch) -> Any:
    fake_pop = _fake_population()
    scenario_id = SCENARIO_IDS[0]
    static = StaticSimulationResult(
        scenario_id=scenario_id,
        population_size=1,
        adoption_count=1,
        adoption_rate=1.0,
        results_by_persona={
            "persona-1": {
                "outcome": "adopt",
                "need_score": 0.7,
                "awareness_score": 0.72,
                "consideration_score": 0.68,
                "purchase_score": 0.64,
                "rejection_stage": None,
                "rejection_reason": None,
            }
        },
        rejection_distribution={},
        random_seed=DEFAULT_SEED,
    )

    fake_state = _SessionState(
        {
            "population": fake_pop,
            "scenario_results": {scenario_id: static},
        }
    )
    fake_st = _FakeStreamlit(
        session_state=fake_state,
        select_values={"selected_scenario": scenario_id},
    )
    return _import_page_module(monkeypatch, "app.pages.3_results", fake_st)


def test_coerce_static_from_model(monkeypatch) -> None:
    module = _import_results_page(monkeypatch)
    static = StaticSimulationResult(
        scenario_id=SCENARIO_IDS[0],
        population_size=1,
        adoption_count=1,
        adoption_rate=1.0,
        results_by_persona={"p1": {"outcome": "adopt"}},
        rejection_distribution={},
        random_seed=DEFAULT_SEED,
    )
    assert module._coerce_static(static) is static


def test_coerce_static_from_dict(monkeypatch) -> None:
    module = _import_results_page(monkeypatch)
    payload = {
        "scenario_id": SCENARIO_IDS[0],
        "population_size": 1,
        "adoption_count": 1,
        "adoption_rate": 1.0,
        "results_by_persona": {"p1": {"outcome": "adopt"}},
        "rejection_distribution": {},
        "random_seed": DEFAULT_SEED,
    }
    coerced = module._coerce_static(payload)
    assert isinstance(coerced, StaticSimulationResult)
    assert coerced.population_size == 1


def test_coerce_static_none(monkeypatch) -> None:
    module = _import_results_page(monkeypatch)
    assert module._coerce_static(None) is None
    assert module._coerce_static({"not_results": True}) is None
