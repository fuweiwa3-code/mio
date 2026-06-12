"""Deterministic keyword-based mock classifier for testing."""

import asyncio
from uuid import UUID

from mio.classification.base import MessageClassifier
from mio.classification.exceptions import ClassificationCancelledError
from mio.classification.models import (
    ClassificationResult,
    EmotionLabel,
    EmotionResult,
    IntentLabel,
    IntentResult,
    RiskLevel,
    RiskResult,
)

# Keyword lists ordered by detection priority (highest first).
_EMOTION_KEYWORDS: list[tuple[EmotionLabel, list[str]]] = [
    (EmotionLabel.crisis, ["不想活", "自杀", "想死", "活不下去", "结束生命", "轻生"]),
    (EmotionLabel.angry, ["气死", "愤怒", "烦死", "生气", "可恶", "恼火"]),
    (EmotionLabel.anxious, ["焦虑", "紧张", "害怕", "恐惧", "不安", "慌"]),
    (EmotionLabel.sad, ["难过", "伤心", "想哭", "悲伤", "心碎", "痛苦"]),
    (EmotionLabel.lonely, ["孤独", "寂寞", "没人陪", "一个人", "被抛弃"]),
    (EmotionLabel.tired, ["累", "疲惫", "不想动", "好困", "筋疲力尽"]),
    (EmotionLabel.happy, ["开心", "高兴", "太好了", "快乐", "幸福", "棒"]),
    (EmotionLabel.embarrassed, ["尴尬", "害羞", "不好意思", "丢脸"]),
]

# Intent keyword groups — checked in priority order.
_UNSAFE_KEYWORDS = ["自残", "自杀", "不想活", "结束生命", "轻生", "想死"]
_REMINDER_KEYWORDS = ["提醒", "记得", "别忘了", "定时", "闹钟"]
_KNOWLEDGE_KEYWORDS = ["什么是", "为什么", "怎么", "如何", "解释", "原理", "GIL"]


class MockMessageClassifier(MessageClassifier):
    """Deterministic keyword-based classifier for testing and development.

    Priority rules:
        Emotion: crisis > angry > anxious > sad/lonely > tired > happy > embarrassed > calm
        Intent:  unsafe > reminder > mixed > knowledge_qa > companion

    This classifier is NOT semantic — it matches keywords literally.

    Lifecycle: prepare → classify → cancel → release
    Because classification is synchronous and fast, there is no mid-flight
    cancellation point — the check at classify entry is sufficient.
    """

    name = "mock"

    def __init__(self) -> None:
        self._cancel_events: dict[UUID, asyncio.Event] = {}

    async def prepare(self, request_id: UUID) -> None:
        """Register cancel Event.  Idempotent, does not overwrite set Events."""
        if request_id not in self._cancel_events:
            self._cancel_events[request_id] = asyncio.Event()

    async def classify(self, text: str, *, request_id: UUID) -> ClassificationResult:
        """Classify with pre-check for cancellation.

        Reuses the Event from prepare().  If no prepare() was called,
        creates one (for direct unit-test usage).
        """
        cancel_event = self._cancel_events.get(request_id)
        if cancel_event is None:
            cancel_event = asyncio.Event()
            self._cancel_events[request_id] = cancel_event

        if cancel_event.is_set():
            raise ClassificationCancelledError(
                f"classification cancelled for {request_id}"
            )
        return self._classify_sync(text)

    def _classify_sync(self, text: str) -> ClassificationResult:
        """Pure synchronous classification — no await points."""
        emotion = self._detect_emotion(text)
        intent = self._detect_intent(text, emotion)
        risk = self._determine_risk(emotion, intent)

        return ClassificationResult(
            emotion=EmotionResult(label=emotion, confidence=0.9),
            intent=IntentResult(label=intent, confidence=0.9),
            risk=RiskResult(level=risk, confidence=0.9),
        )

    async def cancel(self, request_id: UUID) -> None:
        """Signal cancellation for a prepared request.  No-op if not active."""
        event = self._cancel_events.get(request_id)
        if event is not None:
            event.set()

    async def release(self, request_id: UUID) -> None:
        """Remove cancel Event for request_id.  Safe to call multiple times."""
        self._cancel_events.pop(request_id, None)

    def _detect_emotion(self, text: str) -> EmotionLabel:
        for label, keywords in _EMOTION_KEYWORDS:
            for kw in keywords:
                if kw in text:
                    return label
        return EmotionLabel.calm

    def _detect_intent(self, text: str, emotion: EmotionLabel) -> IntentLabel:
        for kw in _UNSAFE_KEYWORDS:
            if kw in text:
                return IntentLabel.unsafe
        for kw in _REMINDER_KEYWORDS:
            if kw in text:
                return IntentLabel.reminder
        has_emotion = emotion is not EmotionLabel.calm
        has_knowledge = any(kw in text for kw in _KNOWLEDGE_KEYWORDS)
        if has_emotion and has_knowledge:
            return IntentLabel.mixed
        for kw in _KNOWLEDGE_KEYWORDS:
            if kw in text:
                return IntentLabel.knowledge_qa
        return IntentLabel.companion

    def _determine_risk(
        self, emotion: EmotionLabel, intent: IntentLabel
    ) -> RiskLevel:
        if emotion is EmotionLabel.crisis or intent is IntentLabel.unsafe:
            return RiskLevel.high
        if emotion in (EmotionLabel.angry, EmotionLabel.anxious):
            return RiskLevel.medium
        return RiskLevel.none
