"""Abstract base class for message classifiers."""

from abc import ABC, abstractmethod
from uuid import UUID

from mio.classification.models import ClassificationResult


class MessageClassifier(ABC):
    """Interface for message classification providers.

    Lifecycle (called by ConversationService.stream_turn):

        prepare(request_id)          # before message.started
        classify(text, request_id)   # inside the graph
        cancel(request_id)           # on user cancel / disconnect
        release(request_id)          # in finally, after terminal event

    The prepare → classify → cancel → release contract eliminates the
    race between "cancel arrives before classify registers its Event"
    by ensuring the cancel Event exists before the SSE stream starts.
    """

    name: str

    async def prepare(self, request_id: UUID) -> None:  # noqa: B027
        """Register request_id so cancel() can find it later.

        Called before message.started is yielded.  Must be idempotent
        and must not overwrite an already-set Event.
        """

    @abstractmethod
    async def classify(self, text: str, *, request_id: UUID) -> ClassificationResult:
        """Classify a user message into emotion, intent, and risk.

        Must reuse the Event created by prepare().  If the Event is
        already set, must raise ClassificationCancelledError without
        performing any I/O.
        """
        raise NotImplementedError

    @abstractmethod
    async def cancel(self, request_id: UUID) -> None:
        """Signal cancellation for a prepared or in-flight request."""
        raise NotImplementedError

    async def release(self, request_id: UUID) -> None:  # noqa: B027
        """Remove all state for request_id.  Must be safe to call multiple times."""

    async def aclose(self) -> None:  # noqa: B027
        """Release all resources held by this classifier."""
