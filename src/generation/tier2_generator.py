"""
Tier 2 (deep narrative) persona generation via progressive LLM attribute sampling.
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

import structlog
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.taxonomy.schema import Persona
    from src.utils.llm import LLMClient

logger = structlog.get_logger(__name__)


class AnchorInference(BaseModel):
    """Structured output for the anchor inference step."""

    core_values: list[str] = Field(min_length=3, max_length=5)
    life_attitude: str
    parent_motivations: list[str] = Field(min_length=2, max_length=4)


class LifeStorySnippet(BaseModel):
    """One biographical event used in the full narrative."""

    title: str
    event: str
    impact: str


class LifeStoryResponse(BaseModel):
    """Structured output for the life story step."""

    stories: list[LifeStorySnippet] = Field(min_length=2, max_length=3)


class Tier2NarrativeGenerator:
    """
    Generates biographical narratives for Tier 2 personas.

    Pipeline: anchor attributes -> values -> life story -> full narrative.
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm = llm_client

    async def generate_narrative(self, persona: Persona) -> Persona:
        """
        Enrich a Tier 1 persona with a deep narrative.

        Args:
            persona: Base Tier 1 persona.

        Returns:
            A copied persona with ``tier="deep"`` and a narrative payload.
        """

        if self.llm.config.llm_mock_enabled:
            return self._generate_mock_narrative(persona)

        anchor_payload = self._build_anchor_payload(persona)
        anchor_response = await self.llm.generate(
            prompt=self._build_anchor_prompt(anchor_payload),
            model="bulk",
            response_format="json",
            schema=AnchorInference,
        )
        anchor = AnchorInference.model_validate_json(anchor_response.text)

        story_response = await self.llm.generate(
            prompt=self._build_life_story_prompt(anchor_payload, anchor),
            model="bulk",
            response_format="json",
            schema=LifeStoryResponse,
        )
        stories = LifeStoryResponse.model_validate_json(story_response.text)

        narrative_response = await self.llm.generate(
            prompt=self._build_narrative_prompt(persona, anchor, stories.stories),
            model="bulk",
            response_format="text",
        )

        narrative = narrative_response.text.strip()
        self._validate_narrative(persona, narrative)

        semantic_memory = dict(persona.semantic_memory)
        semantic_memory["tier2_anchor"] = anchor.model_dump(mode="json")
        semantic_memory["tier2_stories"] = stories.model_dump(mode="json")

        logger.info("tier2_narrative_generated", persona_id=persona.id)
        return persona.model_copy(
            update={
                "tier": "deep",
                "narrative": narrative,
                "semantic_memory": semantic_memory,
            }
        )

    async def generate_batch(
        self, personas: list[Persona], max_concurrency: int = 5
    ) -> list[Persona]:
        """
        Generate narratives for multiple personas with concurrency control.

        Args:
            personas: Personas to enrich.
            max_concurrency: Maximum number of concurrent tasks.

        Returns:
            Deep personas in the same order as the input list.
        """

        semaphore = asyncio.Semaphore(max_concurrency)

        async def _generate(persona: Persona) -> Persona:
            async with semaphore:
                return await self.generate_narrative(persona)

        return await asyncio.gather(*(_generate(persona) for persona in personas))

    def _build_anchor_payload(self, persona: Persona) -> dict[str, Any]:
        flat = persona.to_flat_dict()
        core_demographics = {
            "city_tier": persona.demographics.city_tier,
            "city_name": persona.demographics.city_name,
            "region": persona.demographics.region,
            "parent_age": persona.demographics.parent_age,
            "num_children": persona.demographics.num_children,
            "child_ages": persona.demographics.child_ages,
            "family_structure": persona.demographics.family_structure,
            "household_income_lpa": persona.demographics.household_income_lpa,
            "education_level": persona.education_learning.education_level,
            "employment_status": persona.career.employment_status,
            "dietary_culture": persona.cultural.dietary_culture,
        }

        top_psychographics = sorted(
            (
                (key, value)
                for key, value in flat.items()
                if isinstance(value, float) and 0.0 <= value <= 1.0
            ),
            key=lambda item: abs(item[1] - 0.5),
            reverse=True,
        )[:5]

        return {
            "demographics": core_demographics,
            "top_psychographics": dict(top_psychographics),
        }

    def _build_anchor_prompt(self, anchor_payload: dict[str, Any]) -> str:
        serialized = json.dumps(anchor_payload, indent=2, sort_keys=True)
        return (
            "You are creating a detailed biographical profile for a synthetic person.\n"
            "Here are their core attributes:\n"
            f"{serialized}\n\n"
            "Based on these attributes, infer:\n"
            "1. Their core personal values (3-5 values)\n"
            "2. Their life attitude / worldview (2-3 sentences)\n"
            "3. Their primary motivations as a parent\n\n"
            "Return JSON with keys core_values, life_attitude, parent_motivations."
        )

    def _build_life_story_prompt(
        self, anchor_payload: dict[str, Any], anchor: AnchorInference
    ) -> str:
        serialized = json.dumps(
            {
                "anchor_attributes": anchor_payload,
                "inferred_values": anchor.model_dump(mode="json"),
            },
            indent=2,
            sort_keys=True,
        )
        return (
            "Given this person's profile and values:\n"
            f"{serialized}\n\n"
            "Generate 2-3 specific life story snippets that shaped who they are today.\n"
            "These should be concrete and consistent with their demographics and values.\n"
            "Include at least one story related to their parenting journey.\n\n"
            "Return JSON with a single key stories, whose value is an array of objects "
            "with title, event, and impact."
        )

    def _build_narrative_prompt(
        self,
        persona: Persona,
        anchor: AnchorInference,
        stories: list[LifeStorySnippet],
    ) -> str:
        payload = {
            "persona_attributes": persona.to_flat_dict(),
            "anchor": anchor.model_dump(mode="json"),
            "stories": [story.model_dump(mode="json") for story in stories],
        }
        serialized = json.dumps(payload, indent=2, sort_keys=True)
        return (
            "You are writing a third-person biographical narrative for this person:\n"
            f"{serialized}\n\n"
            "Write a 300-500 word narrative that:\n"
            "- Naturally incorporates demographics, values, and life stories\n"
            "- References at least 10 specific persona attributes\n"
            "- Describes their daily routine and parenting approach\n"
            "- Is coherent with all numeric attributes\n"
            "- Uses Hindi-English code-mixing where culturally appropriate\n"
            "- Avoids generic template phrasing\n\n"
            "Do not list attributes. Weave them into a flowing biography."
        )

    def _validate_narrative(self, persona: Persona, narrative: str) -> None:
        candidates = {
            persona.demographics.city_name.lower(),
            persona.demographics.city_tier.lower(),
            persona.demographics.region.lower(),
            str(persona.demographics.parent_age),
            str(persona.demographics.num_children),
            persona.demographics.family_structure.lower(),
            persona.education_learning.education_level.lower(),
            persona.career.employment_status.lower(),
            persona.cultural.dietary_culture.lower(),
            persona.cultural.primary_language.lower(),
            persona.daily_routine.primary_shopping_platform.lower(),
            persona.daily_routine.breakfast_routine.lower(),
            persona.daily_routine.milk_supplement_current.lower(),
            persona.media.primary_social_platform.lower(),
            persona.lifestyle.parenting_philosophy.lower(),
        }
        candidates.update(str(age) for age in persona.demographics.child_ages)

        lowered = narrative.lower()
        hits = sum(1 for candidate in candidates if candidate and candidate in lowered)
        if hits < 10:
            logger.warning(
                "tier2_narrative_validation_low_references", persona_id=persona.id, hits=hits
            )

    def _generate_mock_narrative(self, persona: Persona) -> Persona:
        anchor = AnchorInference(
            core_values=["care", "practicality", "trust", "consistency"],
            life_attitude=(
                f"{persona.demographics.city_name} has taught her to balance ambition with calm routines. "
                "She prefers sensible choices that feel safe, modern, and worth the money."
            ),
            parent_motivations=["steady growth", "strong immunity", "less daily friction"],
        )
        stories = LifeStoryResponse(
            stories=[
                LifeStorySnippet(
                    title="Back-to-work reset",
                    event=(
                        "When her eldest child started preschool, she rebuilt the family's breakfast "
                        "routine to fit office mornings without skipping nutrition."
                    ),
                    impact="That phase made her more deliberate about planning, labels, and convenience.",
                ),
                LifeStorySnippet(
                    title="Doctor's reassurance",
                    event=(
                        "A reassuring pediatrician visit helped her move away from panic and toward "
                        "steady, preventive habits."
                    ),
                    impact="She now combines research, doctor input, and practical routines.",
                ),
            ]
        )
        child_ages = ", ".join(str(age) for age in persona.demographics.child_ages)
        narrative = (
            f"{persona.demographics.city_name}-based {persona.demographics.parent_age}-year-old "
            f"{persona.career.employment_status.replace('_', ' ')} parent lives in a "
            f"{persona.demographics.family_structure} household with {persona.demographics.num_children} child"
            f"{'' if persona.demographics.num_children == 1 else 'ren'} aged {child_ages}. "
            f"She shops mostly on {persona.daily_routine.primary_shopping_platform}, keeps a "
            f"{persona.daily_routine.breakfast_routine} breakfast routine, and currently relies on "
            f"{persona.daily_routine.milk_supplement_current} as part of the family's nutrition habits. "
            f"Her {persona.education_learning.education_level} education makes her attentive to labels, "
            f"while her {persona.cultural.dietary_culture.replace('_', ' ')} food culture keeps meals grounded "
            f"in familiar tastes. In {persona.demographics.region}, she has learned to mix planning with instinct: "
            f"some mornings are pure juggle, but she still wants structured feeding, practical wellness choices, "
            f"and products that feel transparent and worth the spend. She spends time on "
            f"{persona.media.primary_social_platform}, compares notes with other parents when needed, and usually "
            f"moves between research and doctor guidance before trying something new. The stories that define her are "
            f"simple but specific: going back to work pushed her to build a tighter morning system, and one calm doctor "
            f"conversation reduced the anxiety she used to carry around growth and immunity. That is why her parenting "
            f"style today feels both warm and methodical. She wants fewer food battles, better daily consistency, and "
            f"a routine her child can actually stick with."
        )

        semantic_memory = dict(persona.semantic_memory)
        semantic_memory["tier2_anchor"] = anchor.model_dump(mode="json")
        semantic_memory["tier2_stories"] = stories.model_dump(mode="json")

        return persona.model_copy(
            update={
                "tier": "deep",
                "narrative": narrative,
                "semantic_memory": semantic_memory,
            }
        )
