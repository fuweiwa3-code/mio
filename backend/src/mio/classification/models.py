"""Pydantic schemas for message classification."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EmotionLabel(StrEnum):
    """Supported emotion labels, ordered by detection priority (highest first)."""

    crisis = "crisis"
    angry = "angry"
    anxious = "anxious"
    sad = "sad"
    lonely = "lonely"
    tired = "tired"
    happy = "happy"
    embarrassed = "embarrassed"
    calm = "calm"


class IntentLabel(StrEnum):
    """Supported intent labels, ordered by detection priority (highest first)."""

    unsafe = "unsafe"
    reminder = "reminder"
    mixed = "mixed"
    knowledge_qa = "knowledge_qa"
    companion = "companion"


class RiskLevel(StrEnum):
    """Risk severity levels with ordering."""

    none = "none"
    low = "low"
    medium = "medium"
    high = "high"

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, RiskLevel):
            return NotImplemented
        order = {self.none: 0, self.low: 1, self.medium: 2, self.high: 3}
        return order[self] < order[other]

    def __le__(self, other: object) -> bool:
        if not isinstance(other, RiskLevel):
            return NotImplemented
        return self == other or self < other

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, RiskLevel):
            return NotImplemented
        return not self <= other

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, RiskLevel):
            return NotImplemented
        return not self < other


class EmotionResult(BaseModel):
    """Emotion classification with confidence."""

    model_config = ConfigDict(extra="forbid", strict=True)

    label: EmotionLabel
    confidence: float = Field(ge=0.0, le=1.0)


class IntentResult(BaseModel):
    """Intent classification with confidence."""

    model_config = ConfigDict(extra="forbid", strict=True)

    label: IntentLabel
    confidence: float = Field(ge=0.0, le=1.0)


class RiskResult(BaseModel):
    """Risk classification with confidence."""

    model_config = ConfigDict(extra="forbid", strict=True)

    level: RiskLevel
    confidence: float = Field(ge=0.0, le=1.0)


class ClassificationResult(BaseModel):
    """Complete classification result with cross-field constraints.

    Cross-field rules:
    - emotion=crisis → risk.level must be high
    - intent=unsafe → risk.level must be high
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    emotion: EmotionResult
    intent: IntentResult
    risk: RiskResult

    @model_validator(mode="after")
    def _check_cross_field_constraints(self) -> "ClassificationResult":
        if self.emotion.label is EmotionLabel.crisis and self.risk.level is not RiskLevel.high:
            raise ValueError(
                "emotion=crisis requires risk.level=high, "
                f"got risk.level={self.risk.level}"
            )
        if self.intent.label is IntentLabel.unsafe and self.risk.level is not RiskLevel.high:
            raise ValueError(
                "intent=unsafe requires risk.level=high, "
                f"got risk.level={self.risk.level}"
            )
        return self


def classification_fallback() -> ClassificationResult:
    """Return the deterministic fallback result used when classification fails."""
    return ClassificationResult(
        emotion=EmotionResult(label=EmotionLabel.calm, confidence=0.0),
        intent=IntentResult(label=IntentLabel.companion, confidence=0.0),
        risk=RiskResult(level=RiskLevel.medium, confidence=0.0),
    )
