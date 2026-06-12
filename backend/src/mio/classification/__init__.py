"""Message classification module for emotion, intent, and risk detection."""

from mio.classification.base import MessageClassifier
from mio.classification.exceptions import (
    ClassificationCancelledError,
    ClassificationError,
    ClassificationProviderError,
    ClassificationSchemaInvalidError,
)
from mio.classification.mock import MockMessageClassifier
from mio.classification.models import (
    ClassificationResult,
    EmotionLabel,
    EmotionResult,
    IntentLabel,
    IntentResult,
    RiskLevel,
    RiskResult,
    classification_fallback,
)

__all__ = [
    "ClassificationCancelledError",
    "ClassificationError",
    "ClassificationProviderError",
    "ClassificationResult",
    "ClassificationSchemaInvalidError",
    "EmotionLabel",
    "EmotionResult",
    "IntentLabel",
    "IntentResult",
    "MessageClassifier",
    "MockMessageClassifier",
    "RiskLevel",
    "RiskResult",
    "classification_fallback",
]
