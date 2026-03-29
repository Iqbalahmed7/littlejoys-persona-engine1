"""Response clustering for interview probes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.probing.models import ResponseCluster

if TYPE_CHECKING:
    from src.taxonomy.schema import Persona

CLUSTER_KEYWORDS: dict[str, dict[str, list[str] | str]] = {
    "price_sensitivity": {
        "keywords": [
            "price",
            "cost",
            "expensive",
            "afford",
            "worth",
            "budget",
            "money",
            "spend",
        ],
        "description": "Concerns about price or value for money",
    },
    "forgetfulness": {
        "keywords": ["forgot", "busy", "remind", "remember", "slipped", "routine", "hectic"],
        "description": "Product exited working memory amid busy schedules",
    },
    "taste_decline": {
        "keywords": ["taste", "refused", "didn't like", "boring", "same", "flavour", "enjoy"],
        "description": "Child taste preferences or fatigue with the product",
    },
    "trust_concern": {
        "keywords": ["trust", "safe", "doctor", "pediatrician", "natural", "chemical", "ingredient"],
        "description": "Safety and trust concerns about the product",
    },
    "alternatives": {
        "keywords": [
            "switched",
            "horlicks",
            "homemade",
            "another",
            "alternative",
            "pediasure",
            "bournvita",
        ],
        "description": "Switched to or considered familiar alternatives",
    },
    "convenience": {
        "keywords": ["easy", "convenient", "time", "prepare", "cook", "mix", "effort", "morning"],
        "description": "Convenience and effort required to use the product",
    },
    "positive_experience": {
        "keywords": ["love", "great", "happy", "enjoy", "continue", "reorder", "subscribe", "regular"],
        "description": "Positive experience driving continued use",
    },
}


def _dominant_attributes(members: list[tuple[Persona, str]]) -> dict[str, float]:
    if not members:
        return {}

    flat_dicts = [persona.to_flat_dict() for persona, _ in members]
    candidates: list[tuple[str, float]] = []
    for key in flat_dicts[0]:
        values = [
            float(row[key])
            for row in flat_dicts
            if key in row
            and isinstance(row[key], (int, float))
            and not isinstance(row[key], bool)
            and 0.0 <= float(row[key]) <= 1.0
        ]
        if not values:
            continue

        mean_value = sum(values) / len(values)
        if mean_value > 0.6 or mean_value < 0.4:
            candidates.append((key, mean_value))

    candidates.sort(key=lambda item: (abs(item[1] - 0.5), item[0]), reverse=True)
    return {key: round(value, 2) for key, value in candidates[:10]}


def cluster_responses_mock(
    responses: list[tuple[Persona, str]],
) -> list[ResponseCluster]:
    """Cluster responses using deterministic keyword matching."""

    if not responses:
        return []

    assignments: dict[str, list[tuple[Persona, str]]] = {}
    for persona, text in responses:
        text_lower = text.lower()
        best_cluster = "other"
        best_score = 0

        for cluster_id, cluster_def in CLUSTER_KEYWORDS.items():
            keywords = cluster_def["keywords"]
            assert isinstance(keywords, list)
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > best_score:
                best_score = score
                best_cluster = cluster_id

        assignments.setdefault(best_cluster, []).append((persona, text))

    included_clusters: list[tuple[str, list[tuple[Persona, str]]]] = [
        (cluster_id, members)
        for cluster_id, members in assignments.items()
        if cluster_id != "other" or len(members) >= 2
    ]
    if not included_clusters and "other" in assignments:
        included_clusters = [("other", assignments["other"])]

    total = sum(len(members) for _, members in included_clusters)
    clusters: list[ResponseCluster] = []
    for cluster_id, members in included_clusters:
        description = CLUSTER_KEYWORDS.get(cluster_id, {}).get(
            "description",
            "Responses that did not match a specific theme",
        )
        assert isinstance(description, str)
        clusters.append(
            ResponseCluster(
                theme=cluster_id,
                description=description,
                persona_count=len(members),
                percentage=round(len(members) / total, 3) if total else 0.0,
                representative_quotes=[text[:200] for _, text in members[:3]],
                dominant_attributes=_dominant_attributes(members),
            )
        )

    clusters.sort(key=lambda cluster: (-cluster.persona_count, cluster.theme))
    return clusters
