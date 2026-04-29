from unittest.mock import patch

import pytest

from extractor.config import Settings


class TestSettings:
    def test_settings_has_default_values(self):
        settings = Settings()
        assert settings.OPENROUTER_API_URL == "https://openrouter.ai/api/v1/chat/completions"
        assert settings.VLM_MAX_RETRIES == 5
        assert settings.RABBITMQ_PORT == 5672

    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key", "RABBITMQ_PORT": "5673"})
    def test_settings_loads_from_env(self):
        settings = Settings()
        assert settings.OPENROUTER_API_KEY == "test-key"
        assert settings.RABBITMQ_PORT == 5673

    def test_validate_raises_on_missing_api_key(self):
        settings = Settings()
        settings.OPENROUTER_API_KEY = ""
        with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
            settings.validate()

    def test_validate_raises_on_invalid_api_key_placeholder(self):
        settings = Settings()
        settings.OPENROUTER_API_KEY = "your_openrouter_api_key_here"
        with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
            settings.validate()

    def test_validate_raises_on_invalid_port(self):
        settings = Settings()
        settings.RABBITMQ_PORT = 70000
        with pytest.raises(ValueError, match="RABBITMQ_PORT"):
            settings.validate()

    def test_validate_passes_with_valid_config(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "valid-key")
        settings = Settings()
        settings.validate()

    def test_outputs_dir_creates_directory(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "valid-key")
        monkeypatch.setattr("extractor.config.BASE_DIR", tmp_path)
        settings = Settings()
        settings.BASE_DIR = tmp_path
        output_dir = settings.OUTPUTS_DIR
        assert output_dir.exists()
        assert output_dir.is_dir()
