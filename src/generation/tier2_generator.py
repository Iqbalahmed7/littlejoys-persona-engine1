"""
Tier 2 (deep narrative) persona generation via progressive LLM attribute sampling.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from typing import TYPE_CHECKING, Any

import structlog
from pydantic import BaseModel, Field

from src.utils.display import describe_attribute_value

if TYPE_CHECKING:
    from src.taxonomy.schema import Persona
    from src.utils.llm import LLMClient

logger = structlog.get_logger(__name__)

_TRAIT_PHRASE_OVERRIDES: dict[str, tuple[str, str]] = {
    "health_anxiety": (
        "{subject_cap} worries constantly about whether the children are getting the right nutrition.",
        "{subject_cap} rarely lets health fears spiral and prefers a measured view of everyday nutrition questions.",
    ),
    "budget_consciousness": (
        "Every purchase goes through a mental cost-benefit analysis before it reaches the cart.",
        "{subject_cap} is willing to pay more when something feels genuinely useful and trustworthy.",
    ),
    "social_proof_bias": (
        "{subject_cap} trusts recommendations from other parents more than polished advertising.",
        "{subject_cap} rarely follows the crowd and prefers to make up {possessive} own mind.",
    ),
    "medical_authority_trust": (
        "A pediatrician's reassurance carries real weight in the final decision.",
        "{subject_cap} listens respectfully to doctors but still double-checks claims independently.",
    ),
    "authority_bias": (
        "Expert voices and formal trust signals make new products feel safer to try.",
        "{subject_cap} is skeptical of authority-led messaging unless it matches lived experience.",
    ),
    "supplement_necessity_belief": (
        "{subject_cap} sees supplements as a practical bridge when daily meals feel inconsistent.",
        "{subject_cap} would rather solve nutrition through ordinary food before adding another product.",
    ),
    "simplicity_preference": (
        "{subject_cap} gravitates toward routines that are easy to repeat on rushed mornings.",
        "{subject_cap} does not mind experimenting when a better routine seems possible.",
    ),
    "perceived_time_scarcity": (
        "Time always feels scarce, so convenience matters almost as much as trust.",
        "{subject_cap} can make room for slower routines when they feel worthwhile.",
    ),
    "child_taste_veto": (
        "If the child refuses the taste twice, the experiment is usually over.",
        "{subject_cap} is patient enough to keep trying even if the first reaction is mixed.",
    ),
    "ad_receptivity": (
        "{subject_cap} notices useful product messages quickly when they fit the family's stage of life.",
        "{subject_cap} tends to tune out most marketing unless it feels unusually relevant.",
    ),
}


def _stable_variant_index(value: str, modulo: int) -> int:
    digest = hashlib.md5(value.encode("utf-8")).hexdigest()
    return int(digest, 16) % modulo


def _pronouns(persona: Persona) -> tuple[str, str, str]:
    gender = persona.demographics.parent_gender.lower()
    if gender == "male":
        return ("he", "him", "his")
    if gender == "female":
        return ("she", "her", "her")
    return ("they", "them", "their")


def _trait_phrase(field: str, value: float, subject: str, possessive: str) -> str:
    template_pair = _TRAIT_PHRASE_OVERRIDES.get(field)
    if template_pair is not None:
        template = template_pair[0] if value >= 0.5 else template_pair[1]
        return template.format(
            subject=subject,
            subject_cap=subject.capitalize(),
            possessive=possessive,
        )

    description = describe_attribute_value(field, value)
    if value >= 0.5:
        return f"{subject.capitalize()} shows {description} in day-to-day family decisions."
    return f"{subject.capitalize()} tends to operate with {description} rather than extremes."


def _top_trait_phrases(persona: Persona, limit: int = 5) -> list[str]:
    flat = persona.to_flat_dict()
    subject, _, possessive = _pronouns(persona)
    scored = sorted(
        (
            (field, float(value))
            for field, value in flat.items()
            if isinstance(value, float) and 0.0 <= value <= 1.0
        ),
        key=lambda item: abs(item[1] - 0.5),
        reverse=True,
    )
    return [_trait_phrase(field, value, subject, possessive) for field, value in scored[:limit]]


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
        name = persona.display_name or persona.id
        subject, _, possessive = _pronouns(persona)
        subject_cap = subject.capitalize()
        ages = persona.demographics.child_ages
        child_ages = ", ".join(str(age) for age in ages)
        eldest_age = max(ages) if ages else persona.demographics.oldest_child_age
        household_income = round(persona.demographics.household_income_lpa)
        employment = persona.career.employment_status.replace("_", " ")
        family_structure = persona.demographics.family_structure.replace("_", " ")
        urbanity = persona.demographics.urban_vs_periurban.replace("_", " ")
        dietary_culture = persona.cultural.dietary_culture.replace("_", " ")
        shopping_platform = persona.daily_routine.primary_shopping_platform.replace("_", " ")
        breakfast_routine = persona.daily_routine.breakfast_routine.replace("_", " ")
        milk_routine = persona.daily_routine.milk_supplement_current.replace("_", " ")
        social_platform = persona.media.primary_social_platform.replace("_", " ")
        trait_phrases = _top_trait_phrases(persona)

        anchor = AnchorInference(
            core_values=["care", "practicality", "trust", "consistency"],
            life_attitude=(
                f"{name} tries to balance ambition with steadiness at home. "
                f"{subject_cap} prefers choices that feel trustworthy, practical, and sustainable."
            ),
            parent_motivations=["steady growth", "strong immunity", "less daily friction"],
        )
        stories = LifeStoryResponse(
            stories=[
                LifeStorySnippet(
                    title="Morning reset",
                    event=(
                        f"When {name}'s oldest child reached age {eldest_age}, {subject} rebuilt the "
                        "family's morning routine so breakfast could stay reliable even on rushed days."
                    ),
                    impact=(
                        "That stretch made planning, labels, and convenience feel just as important "
                        "as good intentions."
                    ),
                ),
                LifeStorySnippet(
                    title="Trust, then try",
                    event=(
                        f"A reassuring conversation with a pediatrician, mixed with chats from other "
                        f"parents, helped {name} shift from worry to steadier everyday habits."
                    ),
                    impact=(
                        f"{subject_cap} now blends research, trusted advice, and realistic routines "
                        "before making a purchase."
                    ),
                ),
            ]
        )
        openings = (
            (
                f"Every morning in {persona.demographics.city_name}, {name} begins the day by scanning "
                f"the kitchen, the school schedule, and the mood of the children before {subject} even "
                "thinks about work."
            ),
            (
                f"Growing up in {persona.demographics.region}, {name} learned early that family care is "
                "measured less by grand promises and more by what shows up on the table every day."
            ),
            (
                f"{name} believes that parenting is a long game built on consistency, calm judgment, "
                "and small routines that children can actually live with."
            ),
            (
                f"When {name}'s {eldest_age}-year-old entered a more demanding school routine, {subject} "
                "started rethinking everything from breakfast habits to what counted as a trustworthy buy."
            ),
            (
                f"In the {urbanity} neighborhoods around {persona.demographics.city_name}, {name} moves "
                "through a world of school chatter, delivery apps, family advice, and constant health talk."
            ),
        )
        opening = openings[_stable_variant_index(persona.id, len(openings))]

        paragraph_1 = (
            f"{opening} At {persona.demographics.parent_age}, {subject} is a {employment} parent in a "
            f"{family_structure} household, raising {persona.demographics.num_children} child"
            f"{'' if persona.demographics.num_children == 1 else 'ren'} aged {child_ages}. "
            f"With roughly {household_income} lakh in annual household income and a "
            f"{persona.education_learning.education_level} education, {name} has learned to hold ambition "
            f"and practicality in the same frame."
        )
        paragraph_2 = (
            f"Daily life runs on a {breakfast_routine} breakfast rhythm, familiar {dietary_culture} food, "
            f"and a shopping pattern that leans on {shopping_platform} when it saves time. "
            f"{subject_cap} keeps {milk_routine} in the family's routine, checks in on new ideas through "
            f"{social_platform}, and notices quickly when a product promises convenience without fitting "
            "real family habits."
        )
        paragraph_3 = " ".join(
            [
                f"As a parent, {name} comes across as warm but deliberate.",
                *trait_phrases[:3],
            ]
        )
        paragraph_4 = " ".join(
            [
                f"That is why {possessive} purchase style is careful rather than impulsive.",
                *trait_phrases[3:],
                f"{subject_cap} usually says yes only when trust, daily fit, and visible value all line up at once.",
            ]
        )
        narrative = "\n\n".join([paragraph_1, paragraph_2, paragraph_3, paragraph_4])
        self._validate_narrative(persona, narrative)

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
