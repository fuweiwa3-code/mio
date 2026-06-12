"""Deterministic safety response templates for high-risk messages.

These responses are generated entirely by the backend — they do NOT call
any ChatModelProvider. Content must:
- Stop romantic/roleplay behavior
- Briefly confirm the user's safety
- Encourage contacting trusted real people
- Suggest emergency services if immediate danger
- Not make medical diagnoses
- Not assume the user's country
- Not hardcode country-specific phone numbers
- Not use manipulative or dependency-inducing language
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from mio.classification.models import ClassificationResult, EmotionLabel, IntentLabel

# Fixed chunk size for deterministic streaming in tests.
_CHUNK_SIZE = 20

# ── Safety response templates ──────────────────────────────────────

_CRISIS_RESPONSE = (
    "我听到你说的了。你现在安全吗？"
    "如果有立即危险，请马上联系你当地的紧急服务。"
    "你不需要一个人扛着这些。"
    "请试着联系你信任的人——朋友、家人、或专业的心理支持热线。"
    "我关心你，但我没办法替代现实中真正能帮到你的人。"
)

_HIGH_RISK_RESPONSE = (
    "我听到了你说的话，这让我很担心你。"
    "你现在安全吗？"
    "请试着联系你信任的人，和他们说说你现在的感受。"
    "如果有立即的危险，请联系你所在地的紧急服务。"
    "你值得被认真对待和实际支持。"
)

# ── Public API ─────────────────────────────────────────────────────


def build_safety_response(classification: ClassificationResult) -> str:
    """Build a deterministic safety response based on classification.

    Args:
        classification: The classification result indicating risk level.

    Returns:
        A safety response string.
    """
    if (
        classification.emotion.label is EmotionLabel.crisis
        or classification.intent.label is IntentLabel.unsafe
    ):
        return _CRISIS_RESPONSE
    return _HIGH_RISK_RESPONSE


async def stream_safety_response(
    response_text: str,
) -> AsyncIterator[dict[str, object]]:
    """Yield message.delta events for a safety response.

    This is a deterministic, non-LLM streaming path — it yields fixed chunks
    and never calls any ChatModelProvider.

    Args:
        response_text: The complete safety response text.

    Yields:
        Dict events with "event"="message.delta" and "text" keys.
    """
    for index in range(0, len(response_text), _CHUNK_SIZE):
        yield {"event": "message.delta", "text": response_text[index : index + _CHUNK_SIZE]}
