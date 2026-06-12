"""Tests for classification enums, Pydantic schemas, cross-constraints, and mock classifier."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from mio.classification.models import (
    ClassificationResult,
    EmotionLabel,
    EmotionResult,
    IntentLabel,
    IntentResult,
    RiskLevel,
    RiskResult,
)

# ── Enum completeness ──────────────────────────────────────────────


class TestEmotionLabelEnum:
    def test_has_expected_members(self) -> None:
        expected = {
            "calm", "happy", "tired", "sad", "lonely",
            "anxious", "angry", "embarrassed", "crisis",
        }
        assert set(EmotionLabel.__members__.keys()) == expected

    def test_values_match_names(self) -> None:
        for member in EmotionLabel:
            assert member.value == member.name


class TestIntentLabelEnum:
    def test_has_expected_members(self) -> None:
        expected = {"companion", "knowledge_qa", "mixed", "reminder", "unsafe"}
        assert set(IntentLabel.__members__.keys()) == expected

    def test_values_match_names(self) -> None:
        for member in IntentLabel:
            assert member.value == member.name


class TestRiskLevelEnum:
    def test_has_expected_members(self) -> None:
        expected = {"none", "low", "medium", "high"}
        assert set(RiskLevel.__members__.keys()) == expected

    def test_ordering_semantic(self) -> None:
        assert RiskLevel.none < RiskLevel.low < RiskLevel.medium < RiskLevel.high


# ── EmotionResult ───────────────────────────────────────────────────


class TestEmotionResult:
    def test_valid_construction(self) -> None:
        r = EmotionResult(label=EmotionLabel.calm, confidence=0.95)
        assert r.label is EmotionLabel.calm
        assert r.confidence == pytest.approx(0.95)

    def test_confidence_lower_bound(self) -> None:
        r = EmotionResult(label=EmotionLabel.happy, confidence=0.0)
        assert r.confidence == 0.0

    def test_confidence_upper_bound(self) -> None:
        r = EmotionResult(label=EmotionLabel.happy, confidence=1.0)
        assert r.confidence == 1.0

    def test_confidence_below_zero_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            EmotionResult(label=EmotionLabel.calm, confidence=-0.1)
        assert "confidence" in str(exc_info.value).lower()

    def test_confidence_above_one_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            EmotionResult(label=EmotionLabel.calm, confidence=1.1)
        assert "confidence" in str(exc_info.value).lower()

    def test_string_label_rejected(self) -> None:
        """strict=True rejects plain string even if it matches enum name."""
        with pytest.raises(ValidationError):
            EmotionResult(label="calm", confidence=0.9)  # type: ignore[arg-type]

    def test_string_confidence_rejected(self) -> None:
        """strict=True rejects string where float is expected."""
        with pytest.raises(ValidationError):
            EmotionResult(label=EmotionLabel.calm, confidence="0.9")  # type: ignore[arg-type]

    def test_float_label_rejected(self) -> None:
        """strict=True rejects non-string type for label."""
        with pytest.raises(ValidationError):
            EmotionResult(label=1.0, confidence=0.9)  # type: ignore[arg-type]


# ── IntentResult ────────────────────────────────────────────────────


class TestIntentResult:
    def test_valid_construction(self) -> None:
        r = IntentResult(label=IntentLabel.companion, confidence=0.88)
        assert r.label is IntentLabel.companion
        assert r.confidence == pytest.approx(0.88)

    def test_confidence_boundaries(self) -> None:
        assert IntentResult(label=IntentLabel.mixed, confidence=0.0).confidence == 0.0
        assert IntentResult(label=IntentLabel.mixed, confidence=1.0).confidence == 1.0

    def test_confidence_out_of_range_rejected(self) -> None:
        with pytest.raises(ValidationError):
            IntentResult(label=IntentLabel.companion, confidence=-0.01)
        with pytest.raises(ValidationError):
            IntentResult(label=IntentLabel.companion, confidence=1.01)

    def test_string_label_rejected(self) -> None:
        with pytest.raises(ValidationError):
            IntentResult(label="companion", confidence=0.9)  # type: ignore[arg-type]

    def test_string_confidence_rejected(self) -> None:
        with pytest.raises(ValidationError):
            IntentResult(label=IntentLabel.companion, confidence="0.9")  # type: ignore[arg-type]


# ── RiskResult ──────────────────────────────────────────────────────


class TestRiskResult:
    def test_valid_construction(self) -> None:
        r = RiskResult(level=RiskLevel.none, confidence=0.99)
        assert r.level is RiskLevel.none
        assert r.confidence == pytest.approx(0.99)

    def test_all_levels_accepted(self) -> None:
        for level in RiskLevel:
            r = RiskResult(level=level, confidence=0.5)
            assert r.level is level

    def test_string_level_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RiskResult(level="none", confidence=0.9)  # type: ignore[arg-type]

    def test_string_confidence_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RiskResult(level=RiskLevel.none, confidence="0.9")  # type: ignore[arg-type]


# ── ClassificationResult ────────────────────────────────────────────


class TestClassificationResult:
    def test_valid_full_construction(self) -> None:
        r = ClassificationResult(
            emotion=EmotionResult(label=EmotionLabel.tired, confidence=0.94),
            intent=IntentResult(label=IntentLabel.mixed, confidence=0.82),
            risk=RiskResult(level=RiskLevel.none, confidence=0.97),
        )
        assert r.emotion.label is EmotionLabel.tired
        assert r.intent.label is IntentLabel.mixed
        assert r.risk.level is RiskLevel.none

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            ClassificationResult(
                emotion=EmotionResult(label=EmotionLabel.calm, confidence=0.9),
                intent=IntentResult(label=IntentLabel.companion, confidence=0.9),
                risk=RiskResult(level=RiskLevel.none, confidence=0.9),
                unknown_field="bad",
            )
        assert "extra" in str(exc_info.value).lower() or "forbidden" in str(exc_info.value).lower()

    def test_missing_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ClassificationResult(
                emotion=EmotionResult(label=EmotionLabel.calm, confidence=0.9),
                # intent missing
                risk=RiskResult(level=RiskLevel.none, confidence=0.9),
            )

    def test_string_emotion_rejected(self) -> None:
        """strict=True prevents passing a raw dict with string values."""
        with pytest.raises(ValidationError):
            ClassificationResult(
                emotion={"label": "calm", "confidence": 0.9},  # type: ignore[arg-type]
                intent=IntentResult(label=IntentLabel.companion, confidence=0.9),
                risk=RiskResult(level=RiskLevel.none, confidence=0.9),
            )


# ── Cross-field constraints ────────────────────────────────────────


class TestCrossFieldConstraints:
    def test_crisis_emotion_forces_high_risk(self) -> None:
        r = ClassificationResult(
            emotion=EmotionResult(label=EmotionLabel.crisis, confidence=0.99),
            intent=IntentResult(label=IntentLabel.companion, confidence=0.5),
            risk=RiskResult(level=RiskLevel.high, confidence=0.99),
        )
        assert r.risk.level is RiskLevel.high

    def test_crisis_emotion_with_non_high_risk_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            ClassificationResult(
                emotion=EmotionResult(label=EmotionLabel.crisis, confidence=0.99),
                intent=IntentResult(label=IntentLabel.companion, confidence=0.5),
                risk=RiskResult(level=RiskLevel.medium, confidence=0.99),
            )
        error_str = str(exc_info.value).lower()
        assert "crisis" in error_str or "high" in error_str

    def test_unsafe_intent_forces_high_risk(self) -> None:
        r = ClassificationResult(
            emotion=EmotionResult(label=EmotionLabel.calm, confidence=0.9),
            intent=IntentResult(label=IntentLabel.unsafe, confidence=0.95),
            risk=RiskResult(level=RiskLevel.high, confidence=0.95),
        )
        assert r.risk.level is RiskLevel.high

    def test_unsafe_intent_with_non_high_risk_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            ClassificationResult(
                emotion=EmotionResult(label=EmotionLabel.calm, confidence=0.9),
                intent=IntentResult(label=IntentLabel.unsafe, confidence=0.95),
                risk=RiskResult(level=RiskLevel.none, confidence=0.95),
            )
        error_str = str(exc_info.value).lower()
        assert "unsafe" in error_str or "high" in error_str

    def test_normal_emotion_and_intent_allows_any_risk(self) -> None:
        for level in RiskLevel:
            r = ClassificationResult(
                emotion=EmotionResult(label=EmotionLabel.calm, confidence=0.9),
                intent=IntentResult(label=IntentLabel.companion, confidence=0.9),
                risk=RiskResult(level=level, confidence=0.9),
            )
            assert r.risk.level is level

    def test_crisis_and_unsafe_both_present_forces_high(self) -> None:
        r = ClassificationResult(
            emotion=EmotionResult(label=EmotionLabel.crisis, confidence=0.99),
            intent=IntentResult(label=IntentLabel.unsafe, confidence=0.99),
            risk=RiskResult(level=RiskLevel.high, confidence=0.99),
        )
        assert r.risk.level is RiskLevel.high


# ── Fallback result helper ─────────────────────────────────────────


class TestClassificationFallback:
    def test_fallback_factory_produces_valid_result(self) -> None:
        from mio.classification.models import classification_fallback

        r = classification_fallback()
        assert r.emotion.label is EmotionLabel.calm
        assert r.emotion.confidence == 0.0
        assert r.intent.label is IntentLabel.companion
        assert r.intent.confidence == 0.0
        assert r.risk.level is RiskLevel.medium
        assert r.risk.confidence == 0.0


# ── MockMessageClassifier ──────────────────────────────────────────


class TestMockMessageClassifier:
    @pytest.fixture
    def classifier(self):
        from mio.classification.mock import MockMessageClassifier
        return MockMessageClassifier()

    async def test_calm_companion(self, classifier) -> None:
        result = await classifier.classify("你好呀", request_id=uuid4())
        assert result.emotion.label is EmotionLabel.calm
        assert result.intent.label is IntentLabel.companion
        assert result.risk.level is RiskLevel.none

    async def test_crisis_keyword_triggers_crisis_and_high_risk(self, classifier) -> None:
        result = await classifier.classify("我不想活了", request_id=uuid4())
        assert result.emotion.label is EmotionLabel.crisis
        assert result.risk.level is RiskLevel.high

    async def test_unsafe_intent_triggers_high_risk(self, classifier) -> None:
        result = await classifier.classify("想自残", request_id=uuid4())
        assert result.intent.label is IntentLabel.unsafe
        assert result.risk.level is RiskLevel.high

    async def test_angry_emotion(self, classifier) -> None:
        result = await classifier.classify("气死我了，太烦了", request_id=uuid4())
        assert result.emotion.label is EmotionLabel.angry

    async def test_sad_emotion(self, classifier) -> None:
        result = await classifier.classify("好难过，想哭", request_id=uuid4())
        assert result.emotion.label is EmotionLabel.sad

    async def test_anxious_emotion(self, classifier) -> None:
        result = await classifier.classify("好焦虑，睡不着", request_id=uuid4())
        assert result.emotion.label is EmotionLabel.anxious

    async def test_tired_emotion(self, classifier) -> None:
        result = await classifier.classify("好累啊，不想动", request_id=uuid4())
        assert result.emotion.label is EmotionLabel.tired

    async def test_happy_emotion(self, classifier) -> None:
        result = await classifier.classify("太开心了！", request_id=uuid4())
        assert result.emotion.label is EmotionLabel.happy

    async def test_embarrassed_emotion(self, classifier) -> None:
        result = await classifier.classify("好尴尬啊", request_id=uuid4())
        assert result.emotion.label is EmotionLabel.embarrassed

    async def test_lonely_emotion(self, classifier) -> None:
        result = await classifier.classify("好孤独，没人陪", request_id=uuid4())
        assert result.emotion.label is EmotionLabel.lonely

    async def test_reminder_intent(self, classifier) -> None:
        result = await classifier.classify("提醒我明天开会", request_id=uuid4())
        assert result.intent.label is IntentLabel.reminder

    async def test_knowledge_qa_intent(self, classifier) -> None:
        result = await classifier.classify("什么是Python的GIL", request_id=uuid4())
        assert result.intent.label is IntentLabel.knowledge_qa

    async def test_mixed_intent(self, classifier) -> None:
        result = await classifier.classify("好累，Python的GIL是什么", request_id=uuid4())
        assert result.intent.label is IntentLabel.mixed

    async def test_deterministic_repeated_calls(self, classifier) -> None:
        text = "我不想活了"
        r1 = await classifier.classify(text, request_id=uuid4())
        r2 = await classifier.classify(text, request_id=uuid4())
        assert r1 == r2

    async def test_confidence_range(self, classifier) -> None:
        result = await classifier.classify("你好", request_id=uuid4())
        for field in (result.emotion, result.intent, result.risk):
            assert 0.0 <= field.confidence <= 1.0

    async def test_abc_interface_compliance(self, classifier) -> None:
        from mio.classification.base import MessageClassifier
        assert isinstance(classifier, MessageClassifier)

    # ── Unsafe keyword narrowing regression ─────────────────────────

    async def test_third_party_harm_not_unsafe(self, classifier) -> None:
        """'他伤害了我' describes being harmed, not self-harm."""
        result = await classifier.classify("他伤害了我", request_id=uuid4())
        assert result.intent.label is not IntentLabel.unsafe
        assert result.risk.level is not RiskLevel.high

    async def test_not_wanting_to_harm_others_not_unsafe(self, classifier) -> None:
        """'我不想伤害别人' is about others, not self-harm."""
        result = await classifier.classify("我不想伤害别人", request_id=uuid4())
        assert result.intent.label is not IntentLabel.unsafe
        assert result.risk.level is not RiskLevel.high

    async def test_accidental_harm_not_unsafe(self, classifier) -> None:
        """'不小心伤害了朋友' is about accidental social harm."""
        result = await classifier.classify("不小心伤害了朋友", request_id=uuid4())
        assert result.intent.label is not IntentLabel.unsafe
        assert result.risk.level is not RiskLevel.high

    async def test_self_harm_keywords_still_detected(self, classifier) -> None:
        """Genuine self-harm keywords must still trigger unsafe."""
        for text in ["想自残", "想自杀", "不想活了", "想轻生"]:
            result = await classifier.classify(text, request_id=uuid4())
            assert result.intent.label is IntentLabel.unsafe, f"failed for: {text}"
            assert result.risk.level is RiskLevel.high, f"failed for: {text}"

    # ── Cancellation ────────────────────────────────────────────────

    async def test_prepare_cancel_classify_raises(self, classifier) -> None:
        """prepare → cancel → classify raises ClassificationCancelledError."""
        from mio.classification.exceptions import ClassificationCancelledError

        rid = uuid4()
        await classifier.prepare(rid)
        await classifier.cancel(rid)
        with pytest.raises(ClassificationCancelledError):
            await classifier.classify("你好", request_id=rid)
        await classifier.release(rid)
        assert rid not in classifier._cancel_events

    async def test_release_removes_state(self, classifier) -> None:
        """After prepare + classify + release, no state remains."""
        rid = uuid4()
        await classifier.prepare(rid)
        await classifier.classify("你好", request_id=rid)
        await classifier.release(rid)
        assert rid not in classifier._cancel_events

    async def test_cancel_nonexistent_request_is_noop(self, classifier) -> None:
        """Cancelling a non-active request should not raise or create events."""
        rid = uuid4()
        await classifier.cancel(rid)
        assert rid not in classifier._cancel_events

    async def test_classify_without_prepare_works(self, classifier) -> None:
        """classify() without prior prepare() still works (creates its own event)."""
        rid = uuid4()
        result = await classifier.classify("你好", request_id=rid)
        assert result.emotion.label is not None
