from __future__ import annotations


class DecisionResult:
    """Structured output of CognitiveAgent.decide()."""

    VALID_DECISIONS = {"buy", "trial", "reject", "defer", "research_more"}

    def __init__(
        self,
        decision: str,                      # "buy" | "trial" | "reject" | "defer" | "research_more"
        confidence: float,                   # 0.0-1.0
        reasoning_trace: list[str],          # exactly 5 steps
        key_drivers: list[str],              # top motivators
        objections: list[str],               # blockers raised
        willingness_to_pay_inr: int | None,  # None if rejecting
        follow_up_action: str,               # what they do next
        persona_id: str,                     # for logging
    ):
        self.decision = decision
        self.confidence = confidence
        self.reasoning_trace = reasoning_trace
        self.key_drivers = key_drivers
        self.objections = objections
        self.willingness_to_pay_inr = willingness_to_pay_inr
        self.follow_up_action = follow_up_action
        self.persona_id = persona_id

    def to_dict(self) -> dict:
        return {
            "persona_id": self.persona_id,
            "decision": self.decision,
            "confidence": self.confidence,
            "reasoning_trace": self.reasoning_trace,
            "key_drivers": self.key_drivers,
            "objections": self.objections,
            "willingness_to_pay_inr": self.willingness_to_pay_inr,
            "follow_up_action": self.follow_up_action,
        }
