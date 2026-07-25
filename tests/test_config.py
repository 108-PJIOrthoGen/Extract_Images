from unittest.mock import patch

import pytest
from pydantic import ValidationError

from extractor import config
from extractor.config import Settings
from extractor.exceptions import ConfigurationError


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
        with pytest.raises(ConfigurationError, match="OPENROUTER_API_KEY"):
            settings.validate_runtime()

    def test_validate_raises_on_invalid_api_key_placeholder(self):
        settings = Settings()
        settings.OPENROUTER_API_KEY = "your_openrouter_api_key_here"
        with pytest.raises(ConfigurationError, match="OPENROUTER_API_KEY"):
            settings.validate_runtime()

    @patch.dict("os.environ", {"RABBITMQ_PORT": "70000"})
    def test_settings_rejects_invalid_port_at_load(self):
        # Range validation now happens at load time via pydantic, not in validate().
        with pytest.raises(ValidationError):
            Settings()

    def test_validate_passes_with_valid_config(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "valid-key")
        settings = Settings()
        settings.validate_runtime()

    def test_outputs_dir_creates_directory(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "valid-key")
        monkeypatch.setattr("extractor.config.BASE_DIR", tmp_path)
        settings = Settings()
        settings.BASE_DIR = tmp_path
        output_dir = settings.OUTPUTS_DIR
        assert output_dir.exists()
        assert output_dir.is_dir()

    def test_base_dir_resolves_from_cwd_when_template_exists(self, tmp_path, monkeypatch):
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "template.json").write_text("{}", encoding="utf-8")
        monkeypatch.delenv("BASE_DIR", raising=False)
        monkeypatch.chdir(tmp_path)

        assert config._resolve_base_dir() == tmp_path

    def test_template_path_env_can_be_relative_to_base_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr("extractor.config.BASE_DIR", tmp_path)
        monkeypatch.setenv("TEMPLATE_PATH", "custom/template.json")

        assert config._resolve_template_path() == tmp_path / "custom" / "template.json"
