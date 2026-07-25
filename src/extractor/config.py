"""Centralized configuration with validation (pydantic-settings)."""

import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from extractor.exceptions import ConfigurationError

TEMPLATE_RELATIVE_PATH = Path("templates") / "template.json"


def _resolve_base_dir() -> Path:
    """Resolve the runtime data root independently from package install path."""
    override = os.getenv("BASE_DIR")
    if override:
        return Path(override).expanduser().resolve()

    cwd = Path.cwd().resolve()
    candidates = [cwd, *cwd.parents, Path(__file__).resolve().parent.parent.parent]
    for candidate in candidates:
        if (candidate / TEMPLATE_RELATIVE_PATH).exists():
            return candidate

    return Path(__file__).resolve().parent.parent.parent


def _resolve_template_path() -> Path:
    override = os.getenv("TEMPLATE_PATH")
    if override:
        path = Path(override).expanduser()
        return path.resolve() if path.is_absolute() else (BASE_DIR / path).resolve()
    return BASE_DIR / TEMPLATE_RELATIVE_PATH


BASE_DIR = _resolve_base_dir()

_PLACEHOLDER_API_KEY = "your_openrouter_api_key_here"


def _ensure_dir(path: Path) -> Path:
    """Lazy directory creation -- only create when called, not on import."""
    path.mkdir(parents=True, exist_ok=True)
    return path


class Settings(BaseSettings):
    """Application settings loaded from environment variables / ``.env``.

    Field names are upper-case to match the existing env var names exactly
    (e.g. ``OPENROUTER_API_KEY``); pydantic-settings handles type coercion and
    range validation, replacing the previous hand-rolled ``os.getenv`` parsing.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    BASE_DIR: Path = BASE_DIR

    # Template
    TEMPLATE_PATH: Path = Field(default_factory=_resolve_template_path)

    def model_post_init(self, __context: object) -> None:
        if not self.TEMPLATE_PATH.is_absolute():
            self.TEMPLATE_PATH = (self.BASE_DIR / self.TEMPLATE_PATH).resolve()

    # OpenRouter
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "google/gemini-1.5-pro"
    OPENROUTER_API_URL: str = "https://openrouter.ai/api/v1/chat/completions"

    # OpenRouter routing/transport. Sort = "throughput" routes to the fastest
    # provider; "" = OpenRouter's default. Timeouts (seconds) avoid hanging
    # forever when a provider stalls.
    OPENROUTER_PROVIDER_SORT: str = "throughput"
    VLM_TIMEOUT_CONNECT: float = 10.0
    VLM_TIMEOUT_READ: float = 180.0

    # VLM retry / output budget. The expanded template (~470 fields) needs a high
    # max_tokens so a fully-filled output is not truncated.
    VLM_MAX_RETRIES: int = 5
    VLM_BASE_DELAY: float = 1.0
    VLM_MAX_TOKENS: int = 32768

    # PDF handling (hybrid): a page with at least PDF_TEXT_MIN_CHARS extractable
    # characters is sent to the LLM as TEXT (accurate, cheap); otherwise it is
    # rendered to an image at PDF_RENDER_DPI and sent to the VLM as an image.
    PDF_RENDER_DPI: int = 150
    PDF_TEXT_MIN_CHARS: int = 100

    # Completeness: warn when ``0 < fill_rate < LOW_FILL_RATE_THRESHOLD`` (0..1).
    LOW_FILL_RATE_THRESHOLD: float = 0.5

    # RabbitMQ
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = Field(default=5672, ge=1, le=65535)
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_QUEUE: str = "image_processing"

    # Paths (lazy -- only create on access). Upper-case to match the other
    # settings fields and the established public API (``settings.OUTPUTS_DIR``).
    @property
    def OUTPUTS_DIR(self) -> Path:  # noqa: N802
        override = os.getenv("OUTPUTS_DIR")
        return _ensure_dir(Path(override) if override else self.BASE_DIR / "outputs")

    @property
    def UPLOAD_DIR(self) -> Path:  # noqa: N802
        override = os.getenv("UPLOAD_DIR")
        return _ensure_dir(Path(override) if override else self.BASE_DIR / "uploads")

    def validate_runtime(self) -> None:
        """Raise :class:`ConfigurationError` if config is unusable at runtime.

        Named ``validate_runtime`` (not ``validate``) to avoid clashing with
        pydantic ``BaseModel.validate``. Type/range checks (e.g. RABBITMQ_PORT)
        are enforced by pydantic at load time; this only covers the
        "must be set by the operator" API key.
        """
        if not self.OPENROUTER_API_KEY or self.OPENROUTER_API_KEY == _PLACEHOLDER_API_KEY:
            raise ConfigurationError("OPENROUTER_API_KEY chua duoc thiet lap hoac khong hop le.")


settings = Settings()
