"""Tests for classifier factory and config integration."""

import pytest

from mio.classification.factory import create_message_classifier
from mio.classification.mock import MockMessageClassifier
from mio.classification.openai_compatible import OpenAICompatibleMessageClassifier
from mio.config import Settings


class TestClassifierConfig:
    def test_default_classifier_provider_is_mock(self) -> None:
        settings = Settings(environment="test")
        assert settings.classifier_provider == "mock"

    def test_default_classifier_model(self) -> None:
        settings = Settings(environment="test")
        assert settings.classifier_model == "mock-classifier"

    def test_default_classifier_base_url_is_empty(self) -> None:
        settings = Settings(environment="test")
        assert settings.classifier_base_url == ""

    def test_default_classifier_api_key_is_empty(self) -> None:
        settings = Settings(environment="test")
        assert settings.classifier_api_key == ""

    def test_env_prefix_is_mio(self) -> None:
        """Verify classifier settings use MIO_ prefix."""
        settings = Settings(
            environment="test",
            classifier_provider="openai_compatible",
            classifier_model="gpt-4o-mini",
            classifier_base_url="https://api.example.com/v1",
            classifier_api_key="sk-test",
        )
        assert settings.classifier_provider == "openai_compatible"
        assert settings.classifier_model == "gpt-4o-mini"
        assert settings.classifier_base_url == "https://api.example.com/v1"
        assert settings.classifier_api_key == "sk-test"


class TestClassifierFactory:
    def test_default_returns_mock(self) -> None:
        settings = Settings(environment="test")
        classifier = create_message_classifier(settings)
        assert isinstance(classifier, MockMessageClassifier)

    def test_explicit_mock_returns_mock(self) -> None:
        settings = Settings(environment="test", classifier_provider="mock")
        classifier = create_message_classifier(settings)
        assert isinstance(classifier, MockMessageClassifier)

    def test_openai_compatible_returns_correct_type(self) -> None:
        settings = Settings(
            environment="test",
            classifier_provider="openai_compatible",
            classifier_base_url="https://api.example.com/v1",
            classifier_api_key="sk-test",
            classifier_model="gpt-4o-mini",
        )
        classifier = create_message_classifier(settings)
        assert isinstance(classifier, OpenAICompatibleMessageClassifier)

    def test_openai_compatible_missing_base_url_raises(self) -> None:
        settings = Settings(
            environment="test",
            classifier_provider="openai_compatible",
            classifier_base_url="",
            classifier_model="gpt-4o-mini",
        )
        with pytest.raises(ValueError, match="MIO_CLASSIFIER_BASE_URL"):
            create_message_classifier(settings)

    def test_env_example_does_not_contain_real_keys(self) -> None:
        """Verify .env.example has no real API keys."""
        from pathlib import Path

        env_example = Path(__file__).resolve().parents[1] / ".env.example"
        content = env_example.read_text()
        for line in content.splitlines():
            if line.startswith("MIO_CLASSIFIER_API_KEY"):
                assert "=" in line
                _, value = line.split("=", maxsplit=1)
                assert value.strip() == ""
