"""
Tier 1 (statistical) persona generation pipeline.

Orchestrates: demographics sampling → copula → conditional rules → categorical assignment.
Full implementation in PRD-001 / PRD-003 (Cursor).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.taxonomy.schema import Persona


class Tier1Generator:
    """Generates statistically grounded Tier 1 personas."""

    def generate(self, n: int, seed: int) -> list[Persona]:
        """
        Generate n Tier 1 personas with correlated attributes.

        Args:
            n: Number of personas.
            seed: Random seed for reproducibility.

        Returns:
            List of validated Tier 1 Persona objects.
        """
        raise NotImplementedError("Full implementation in PRD-001 / PRD-003")

    @staticmethod
    def enforce_hard_constraints(persona_dict: dict) -> dict:
        """
        Post-sample constraint enforcement for known anti-correlation violations.

        Rules enforced:
            R014: risk_tolerance > 0.75 -> cap loss_aversion at 0.65
            R014: loss_aversion > 0.75 -> cap risk_tolerance at 0.65
            R017: analysis_paralysis > 0.8 -> cap decision_speed at 0.60
            R017: decision_speed > 0.8 -> cap analysis_paralysis at 0.60
            R027: supplement_necessity > 0.8 -> cap food_first_belief at 0.70
            R027: food_first_belief > 0.85 -> cap supplement_necessity at 0.70
            R020: impulse_purchase > 0.85 -> cap analysis_paralysis at 0.60
            R020: analysis_paralysis > 0.85 -> cap impulse_purchase at 0.60
            R030: single_parent -> force child_nutrition decision right to mother_final
        """
        psych = persona_dict.get("psychology", {})
        values = persona_dict.get("values", {})
        daily = persona_dict.get("daily_routine", {})
        demo = persona_dict.get("demographics", {})

        risk = psych.get("risk_tolerance", 0.5)
        loss = psych.get("loss_aversion", 0.5)
        if risk > 0.75 and loss > 0.65:
            psych["loss_aversion"] = 0.65
        if loss > 0.75 and risk > 0.65:
            psych["risk_tolerance"] = 0.65

        paralysis = psych.get("analysis_paralysis_tendency", 0.5)
        speed = psych.get("decision_speed", 0.5)
        if paralysis > 0.8 and speed > 0.60:
            psych["decision_speed"] = 0.60
        if speed > 0.8 and paralysis > 0.60:
            psych["analysis_paralysis_tendency"] = 0.60

        necessity = values.get("supplement_necessity_belief", 0.5)
        food_first = values.get("food_first_belief", 0.5)
        if necessity > 0.8 and food_first > 0.70:
            values["food_first_belief"] = 0.70
        if food_first > 0.85 and necessity > 0.70:
            values["supplement_necessity_belief"] = 0.70

        impulse = daily.get("impulse_purchase_tendency", 0.5)
        if impulse > 0.85 and paralysis > 0.60:
            psych["analysis_paralysis_tendency"] = 0.60
        if paralysis > 0.85 and impulse > 0.60:
            daily["impulse_purchase_tendency"] = 0.60

        if demo.get("family_structure") == "single_parent":
            rights = persona_dict.setdefault("decision_rights", {})
            if rights.get("child_nutrition") in ("father_final", "joint"):
                rights["child_nutrition"] = "mother_final"
            if rights.get("supplements") == "joint":
                rights["supplements"] = "mother_final"

        persona_dict["psychology"] = psych
        persona_dict["values"] = values
        persona_dict["daily_routine"] = daily
        return persona_dict
