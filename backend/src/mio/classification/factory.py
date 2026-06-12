"""Factory for creating MessageClassifier instances from settings."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mio.classification.base import MessageClassifier
from mio.classification.mock import MockMessageClassifier

if TYPE_CHECKING:
    from mio.config import Settings


def create_message_classifier(settings: Settings) -> MessageClassifier:
    """Create a MessageClassifier based on settings.

    Args:
        settings: Application settings with classifier configuration.

    Returns:
        A MessageClassifier instance.

    Raises:
        ValueError: If openai_compatible is selected but base_url is missing.
    """
    if settings.classifier_provider == "openai_compatible":
        if not settings.classifier_base_url:
            raise ValueError(
                "MIO_CLASSIFIER_BASE_URL is required for openai_compatible classifier"
            )
        from mio.classification.openai_compatible import (
            OpenAICompatibleMessageClassifier,
        )

        return OpenAICompatibleMessageClassifier(
            base_url=settings.classifier_base_url,
            api_key=settings.classifier_api_key,
            model=settings.classifier_model,
        )
    return MockMessageClassifier()
