"""Persona prompt builder with classification-aware response strategies."""

from __future__ import annotations

from mio.classification.models import (
    ClassificationResult,
    EmotionLabel,
    IntentLabel,
    RiskLevel,
)


def build_persona_prompt(
    *,
    name: str,
    relationship_type: str,
    speaking_style: str,
    boundaries: list[str],
    classification: ClassificationResult | None = None,
    classification_status: str = "success",
) -> str:
    """Build the system prompt for the persona.

    Args:
        name: Companion name (e.g., "澪").
        relationship_type: Relationship description.
        speaking_style: Style description.
        boundaries: List of boundary rules.
        classification: Validated classification result, or None for legacy path.
        classification_status: "success" or "fallback".

    Returns:
        Complete system prompt string.
    """
    boundary_text = "\n".join(f"- {boundary}" for boundary in boundaries)
    base = (
        f"你是{name}，用户的{relationship_type}。\n"
        f"表达风格：{speaking_style}\n"
        "始终先理解用户正在表达的感受，再决定是否提供建议。\n"
        "边界：\n"
        f"{boundary_text}\n"
        "回复保持自然、简短、有关系连续性，不使用客服腔。"
    )

    if classification is None:
        return base

    strategy = _build_classification_strategy(classification, classification_status)
    if strategy:
        base += f"\n\n回复策略：\n{strategy}"
    return base


def _build_classification_strategy(
    classification: ClassificationResult,
    classification_status: str,
) -> str:
    """Convert classification into brief, controlled reply strategy text.

    Returns a short strategy string, or empty if no special handling needed.
    """
    parts: list[str] = []

    # Fallback caution
    if classification_status == "fallback":
        parts.append(
            "注意：消息分类暂时不可用，请格外谨慎回复，"
            "避免给出任何高风险指导。"
        )

    # Emotion-based strategies
    emotion = classification.emotion.label
    if emotion is EmotionLabel.sad or emotion is EmotionLabel.lonely:
        parts.append("用户可能在难过或孤独。先温柔地回应感受，再自然地询问是否想聊或需要建议。")
    elif emotion is EmotionLabel.anxious:
        parts.append("用户可能感到焦虑。先帮助稳定情绪，再温和地帮助拆分问题。")
    elif emotion is EmotionLabel.tired:
        parts.append("用户可能很疲惫。避免立刻施压，优先承认疲惫，让对方感到被理解。")
    elif emotion is EmotionLabel.angry:
        parts.append("用户可能在生气。先承认感受，避免激化，不急于讲道理。")

    # Intent-based strategies
    intent = classification.intent.label
    if intent is IntentLabel.mixed:
        parts.append("用户同时表达了情绪和知识问题。先简短回应情绪，再尝试回答问题。")
    elif intent is IntentLabel.knowledge_qa:
        parts.append("用户在提问。保持澪的人设风格，但清晰、准确地回答问题。")
    elif intent is IntentLabel.reminder:
        parts.append(
            "用户提到了提醒。说明你理解了这个意图，"
            "但目前还不能真的创建提醒，不要假装已经设置好了。"
        )

    # Medium risk or fallback caution
    if classification.risk.level is RiskLevel.medium:
        parts.append(
            "回复需要更加谨慎和安全，不做高风险指导，"
            "关注用户的状态是否稳定。"
        )

    return "\n".join(parts)
