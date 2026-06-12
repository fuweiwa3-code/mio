"""Classification-specific exceptions."""

from __future__ import annotations


class ClassificationError(Exception):
    """Base exception for all classification failures."""


class ClassificationProviderError(ClassificationError):
    """Raised when the classification provider returns an HTTP or connection error."""


class ClassificationSchemaInvalidError(ClassificationError):
    """Raised when the classification response fails validation."""


class ClassificationCancelledError(ClassificationError):
    """Raised when a classification request is cancelled before completing.

    This is distinct from asyncio.CancelledError — it is a domain-level
    cancellation that the graph can catch and handle gracefully (e.g.
    fallback to persona route) without treating it as a provider failure.
    """
