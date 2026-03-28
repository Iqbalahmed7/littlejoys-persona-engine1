"""
Population orchestrator — end-to-end generation of Tier 1 + Tier 2 personas.

See ARCHITECTURE.md §6 and PRD-003 for full specification.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import structlog
from pydantic import BaseModel, ConfigDict, Field
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from src.constants import (
    DEFAULT_DEEP_PERSONA_COUNT,
    DEFAULT_POPULATION_SIZE,
    DEFAULT_SEED,
    DEMOGRAPHIC_FILTER_MAX_ATTEMPTS,
    DEMOGRAPHIC_FILTER_OVERSAMPLE_MULTIPLIER,
    MAX_PERSONA_VALIDATION_RETRIES,
    MIN_TIER2_SELECTION_SIZE,
    POPULATION_ENGINE_VERSION,
    TIER2_KMEANS_N_INIT,
)
from src.taxonomy.correlations import (
    ConditionalRuleEngine,
    GaussianCopulaGenerator,
    default_psych_correlation_rules,
)
from src.taxonomy.distributions import DistributionTables
from src.taxonomy.schema import Persona, list_psychographic_continuous_attributes
from src.taxonomy.validation import PersonaValidator, PopulationValidationReport

log = structlog.get_logger(__name__)

_CONTINUOUS_ATTR_NAMES: tuple[str, ...] = list_psychographic_continuous_attributes()


class GenerationParams(BaseModel):
    """Parameters used to generate a population."""

    size: int
    seed: int
    deep_persona_count: int
    target_filters: dict[str, Any] = Field(default_factory=dict)


class PopulationMetadata(BaseModel):
    """Metadata about a generated population."""

    generation_timestamp: str
    generation_duration_seconds: float
    engine_version: str
    personas_skipped_after_validation: int = 0
    validation_retry_attempts: int = 0


class Population(BaseModel):
    """Container for a generated population with validation report."""

    id: str
    generation_params: GenerationParams
    tier1_personas: list[Persona]
    tier2_personas: list[Persona]
    validation_report: PopulationValidationReport | None = None
    metadata: PopulationMetadata

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def get_persona(self, persona_id: str) -> Persona:
        """
        Look up a persona by ID across Tier 1 and Tier 2.

        Args:
            persona_id: Persona identifier.

        Returns:
            Matching ``Persona``.

        Raises:
            KeyError: If no persona matches ``persona_id``.
        """
        for persona in self.tier2_personas:
            if persona.id == persona_id:
                return persona
        for persona in self.tier1_personas:
            if persona.id == persona_id:
                return persona
        raise KeyError(persona_id)

    def filter(self, **kwargs: Any) -> list[Persona]:
        """
        Filter personas whose flattened identity attributes match all constraints.

        Args:
            **kwargs: Attribute name → expected value (equality). List values of two
                ints/floats are treated as inclusive ``[low, high]`` for that key.

        Returns:
            All matching personas from Tier 1 and Tier 2 (Tier 2 first in iteration).
        """

        def _matches(flat: dict[str, Any]) -> bool:
            for key, expected in kwargs.items():
                actual = flat.get(key)
                if isinstance(expected, (list, tuple)) and len(expected) == 2:
                    low, high = expected
                    if not isinstance(low, (int, float)) or not isinstance(high, (int, float)):
                        if actual != expected:
                            return False
                        continue
                    if actual is None or not (low <= actual <= high):
                        return False
                elif actual != expected:
                    return False
            return True

        out: list[Persona] = []
        for persona in (*self.tier2_personas, *self.tier1_personas):
            if _matches(persona.to_flat_dict()):
                out.append(persona)
        return out

    def to_dataframe(self) -> pd.DataFrame:
        """
        Flatten all Tier 1 and Tier 2 personas into one DataFrame.

        Returns:
            DataFrame with ``id``, ``tier``, and all identity columns.
        """
        rows: list[dict[str, Any]] = []
        for persona in (*self.tier1_personas, *self.tier2_personas):
            flat = persona.to_flat_dict()
            flat["id"] = persona.id
            flat["tier"] = persona.tier
            rows.append(flat)
        return pd.DataFrame(rows)

    def save(self, path: Path) -> None:
        """
        Persist Tier 1 as Parquet, Tier 2 as JSON files, and metadata as JSON.

        Args:
            path: Directory to create or reuse for this population export.
        """
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        meta_path = path / "population_meta.json"
        tier1_path = path / "tier1.parquet"
        tier2_dir = path / "tier2"
        tier2_dir.mkdir(exist_ok=True)

        tier1_df = pd.DataFrame(
            {"persona_json": [p.model_dump_json() for p in self.tier1_personas]},
        )
        tier1_df.to_parquet(tier1_path, index=False)

        tier2_ids: list[str] = []
        for persona in self.tier2_personas:
            tier2_ids.append(persona.id)
            out_file = tier2_dir / f"{persona.id}.json"
            out_file.write_text(persona.model_dump_json(indent=2), encoding="utf-8")

        payload = {
            "population_id": self.id,
            "generation_params": self.generation_params.model_dump(mode="json"),
            "metadata": self.metadata.model_dump(mode="json"),
            "validation_report": self.validation_report.model_dump(mode="json")
            if self.validation_report
            else None,
            "tier1_parquet": tier1_path.name,
            "tier2_directory": tier2_dir.name,
            "tier2_ids": tier2_ids,
        }
        meta_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        log.info(
            "population_saved",
            path=str(path),
            tier1=len(self.tier1_personas),
            tier2=len(tier2_ids),
        )

    @classmethod
    def load(cls, path: Path) -> Population:
        """
        Load a population written by :meth:`save`.

        Args:
            path: Directory containing ``population_meta.json``.

        Returns:
            Reconstructed ``Population`` instance.
        """
        path = Path(path)
        meta_path = path / "population_meta.json"
        raw = json.loads(meta_path.read_text(encoding="utf-8"))
        generation_params = GenerationParams.model_validate(raw["generation_params"])
        metadata = PopulationMetadata.model_validate(raw["metadata"])
        validation_report = (
            PopulationValidationReport.model_validate(raw["validation_report"])
            if raw.get("validation_report")
            else None
        )

        tier1_df = pd.read_parquet(path / raw["tier1_parquet"])
        tier1_personas = [
            Persona.model_validate_json(row["persona_json"]) for _, row in tier1_df.iterrows()
        ]

        tier2_personas: list[Persona] = []
        tier2_dir = path / raw["tier2_directory"]
        for tid in raw["tier2_ids"]:
            pdata = json.loads((tier2_dir / f"{tid}.json").read_text(encoding="utf-8"))
            tier2_personas.append(Persona.model_validate(pdata))

        return cls(
            id=raw["population_id"],
            generation_params=generation_params,
            tier1_personas=tier1_personas,
            tier2_personas=tier2_personas,
            validation_report=validation_report,
            metadata=metadata,
        )


class PopulationGenerator:
    """
    Orchestrates end-to-end population generation.

    Pipeline: demographics → psychographics (copula) → conditional rules → personas → validation → Tier 2.
    """

    def __init__(self) -> None:
        self._correlation_rules = default_psych_correlation_rules()

    def generate(
        self,
        size: int = DEFAULT_POPULATION_SIZE,
        seed: int = DEFAULT_SEED,
        deep_persona_count: int = DEFAULT_DEEP_PERSONA_COUNT,
        target_filters: dict[str, Any] | None = None,
    ) -> Population:
        """
        Generate a validated population with statistical Tier 1 and a diverse Tier 2 subset.

        Args:
            size: Number of Tier 1 personas to produce (best effort if validation skips rows).
            seed: Master RNG seed for reproducibility.
            deep_persona_count: Number of Tier 2 (``deep``) personas to select for enrichment.
            target_filters: Optional demographic filters (equality or ``[low, high]`` ranges).

        Returns:
            ``Population`` with metadata and optional population validation report.

        Raises:
            ValueError: If filtered demographic sampling cannot supply ``size`` rows.
        """
        t0 = time.perf_counter()
        filters = dict(target_filters or {})
        # Derive population_id from seed for determinism (same seed → same ID)
        population_id = hashlib.md5(f"{seed}-{size}-{filters}".encode()).hexdigest()
        timestamp = datetime.now(UTC).isoformat()

        log.info("population_generation_started", size=size, seed=seed, filters=filters or None)

        demographics = _sample_demographics_filtered(size, seed, filters)
        copula = GaussianCopulaGenerator(self._correlation_rules)
        psychographics = copula.generate(len(demographics), demographics, seed)
        merged = pd.concat(
            [demographics.reset_index(drop=True), psychographics.reset_index(drop=True)],
            axis=1,
        )
        merged = ConditionalRuleEngine().apply(merged)

        validator = PersonaValidator()
        tier1_personas: list[Persona] = []
        skipped = 0
        retry_events = 0

        for i in range(len(merged)):
            persona_id = f"{population_id}-t1-{i:05d}"
            row = merged.iloc[i]
            persona, ok, retries = self._build_persona_with_retries(
                row=row,
                persona_id=persona_id,
                base_seed=seed,
                index=i,
                timestamp=timestamp,
                validator=validator,
            )
            retry_events += retries
            if ok and persona is not None:
                tier1_personas.append(persona)
            else:
                skipped += 1
                log.warning(
                    "persona_skipped_after_validation", persona_id=persona_id, retries=retries
                )

        log.info(
            "validation_complete",
            accepted=len(tier1_personas),
            skipped=skipped,
            retry_attempts=retry_events,
        )

        k_deep = min(deep_persona_count, len(tier1_personas))
        tier2_source = self._select_for_tier2(tier1_personas, k_deep, seed)
        tier2_personas = [
            p.model_copy(
                update={
                    "tier": "deep",
                    "id": f"{population_id}-t2-{j:04d}",
                    "narrative": None,
                }
            )
            for j, p in enumerate(tier2_source)
        ]

        log.info("tier2_selected", count=len(tier2_personas), kmeans_clusters=k_deep)

        flat_pop = [p.to_flat_dict() | {"id": p.id, "tier": p.tier} for p in tier1_personas]
        validation_report = validator.validate_population(flat_pop, {}, {})

        duration = time.perf_counter() - t0
        metadata = PopulationMetadata(
            generation_timestamp=timestamp,
            generation_duration_seconds=duration,
            engine_version=POPULATION_ENGINE_VERSION,
            personas_skipped_after_validation=skipped,
            validation_retry_attempts=retry_events,
        )

        population = Population(
            id=population_id,
            generation_params=GenerationParams(
                size=size,
                seed=seed,
                deep_persona_count=deep_persona_count,
                target_filters=filters,
            ),
            tier1_personas=tier1_personas,
            tier2_personas=tier2_personas,
            validation_report=validation_report,
            metadata=metadata,
        )

        log.info(
            "population_generated",
            population_id=population_id,
            tier1=len(tier1_personas),
            tier2=len(tier2_personas),
            duration_seconds=round(duration, 3),
        )
        return population

    def _build_persona_with_retries(
        self,
        row: pd.Series,
        persona_id: str,
        base_seed: int,
        index: int,
        timestamp: str,
        validator: PersonaValidator,
    ) -> tuple[Persona | None, bool, int]:
        """
        Build and validate a persona, resampling the merged row on hard failures.

        Returns:
            Tuple of (persona or None, success flag, number of retry rounds used).
        """
        retries_used = 0
        current_row = row
        for attempt in range(MAX_PERSONA_VALIDATION_RETRIES + 1):
            if attempt > 0:
                retries_used += 1
                resample_seed = base_seed + index * 10_007 + attempt * 1_009
                current_row = _resample_merged_row(resample_seed, self._correlation_rules)
            flat = _series_to_flat_dict(current_row)
            try:
                persona = Persona.from_flat_dict(
                    flat,
                    persona_id=persona_id,
                    seed=base_seed + index,
                    timestamp=timestamp,
                    tier="statistical",
                )
            except Exception as exc:
                log.warning("persona_construct_failed", persona_id=persona_id, error=str(exc))
                continue

            result = validator.validate_persona(persona_id, persona.to_flat_dict())
            if result.is_valid:
                return persona, True, retries_used

        return None, False, retries_used

    def _select_for_tier2(self, personas: list[Persona], count: int, seed: int) -> list[Persona]:
        """
        Select diverse personas using k-means centroids on normalized continuous attributes.

        Args:
            personas: Pool of Tier 1 personas.
            count: Target number of selections.
            seed: RNG seed for ``KMeans``.

        Returns:
            Up to ``count`` personas closest to distinct cluster centroids.
        """
        if count <= 0 or not personas:
            return []
        if len(personas) <= MIN_TIER2_SELECTION_SIZE:
            return personas[:count]

        k = min(count, len(personas))
        matrix = np.zeros((len(personas), len(_CONTINUOUS_ATTR_NAMES)), dtype=np.float64)
        for i, persona in enumerate(personas):
            flat = persona.to_flat_dict()
            for j, name in enumerate(_CONTINUOUS_ATTR_NAMES):
                val = flat.get(name)
                matrix[i, j] = float(val) if isinstance(val, (int, float)) else 0.0

        scaler = StandardScaler()
        scaled = scaler.fit_transform(matrix)
        kmeans = KMeans(
            n_clusters=k,
            random_state=seed % (2**32),
            n_init=TIER2_KMEANS_N_INIT,
        )
        labels = kmeans.fit_predict(scaled)
        centers = kmeans.cluster_centers_

        selected: list[Persona] = []
        used_indices: set[int] = set()
        for cluster_id in range(k):
            members = np.where(labels == cluster_id)[0]
            if members.size == 0:
                continue
            dists = np.linalg.norm(scaled[members] - centers[cluster_id], axis=1)
            best_local = int(members[int(np.argmin(dists))])
            if best_local in used_indices:
                continue
            used_indices.add(best_local)
            selected.append(personas[best_local])

        if len(selected) < k:
            for idx, persona in enumerate(personas):
                if len(selected) >= k:
                    break
                if idx not in used_indices:
                    used_indices.add(idx)
                    selected.append(persona)

        return selected[:k]


def _filter_demographics_row(filters: dict[str, Any], row: pd.Series) -> bool:
    for key, expected in filters.items():
        actual = row[key]
        if isinstance(expected, (list, tuple)) and len(expected) == 2:
            low, high = expected
            if isinstance(low, (int, float)) and isinstance(high, (int, float)):
                if not (low <= actual <= high):
                    return False
                continue
        if actual != expected:
            return False
    return True


def _sample_demographics_filtered(n: int, seed: int, filters: dict[str, Any]) -> pd.DataFrame:
    tables = DistributionTables()
    if not filters:
        return tables.sample_demographics(n, seed)

    rows: list[pd.Series] = []
    attempt = 0
    while len(rows) < n and attempt < DEMOGRAPHIC_FILTER_MAX_ATTEMPTS:
        batch_size = max(
            n,
            min(n * DEMOGRAPHIC_FILTER_OVERSAMPLE_MULTIPLIER, n + 50),
        )
        batch = tables.sample_demographics(batch_size, seed + attempt)
        for _, row in batch.iterrows():
            if len(rows) >= n:
                break
            if _filter_demographics_row(filters, row):
                rows.append(row)
        attempt += 1

    if len(rows) < n:
        msg = (
            f"Demographic filters matched only {len(rows)} rows after "
            f"{DEMOGRAPHIC_FILTER_MAX_ATTEMPTS} attempts; need {n}."
        )
        raise ValueError(msg)

    return pd.DataFrame(rows).reset_index(drop=True)


def _resample_merged_row(seed: int, correlation_rules: dict[tuple[str, str], float]) -> pd.Series:
    tables = DistributionTables()
    demo = tables.sample_demographics(1, seed)
    copula = GaussianCopulaGenerator(correlation_rules)
    psych = copula.generate(1, demo, seed)
    merged = pd.concat([demo.reset_index(drop=True), psych.reset_index(drop=True)], axis=1)
    merged = ConditionalRuleEngine().apply(merged)
    return merged.iloc[0]


def _series_to_flat_dict(row: pd.Series) -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, (list, tuple)):
            flat[key] = [_scalar_to_python(x) for x in value]
        elif isinstance(value, np.ndarray):
            flat[key] = [_scalar_to_python(x) for x in value.tolist()]
        else:
            flat[key] = _scalar_to_python(value)
    return flat


def _scalar_to_python(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    return value
