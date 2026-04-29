"""Centralized configuration with validation."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _ensure_dir(path: Path) -> Path:
    """Lazy directory creation -- only create when called, not on import."""
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass
class Settings:
    """Application settings loaded from environment variables."""

    BASE_DIR: Path = field(default_factory=lambda: BASE_DIR)

    # Template
    TEMPLATE_PATH: Path = field(
        default_factory=lambda: BASE_DIR / "templates" / "template.json"
    )

    # OpenRouter
    OPENROUTER_API_KEY: str = field(
        default_factory=lambda: os.getenv("OPENROUTER_API_KEY", "")
    )
    OPENROUTER_MODEL: str = field(
        default_factory=lambda: os.getenv(
            "OPENROUTER_MODEL", "google/gemini-1.5-pro"
        )
    )
    OPENROUTER_API_URL: str = "https://openrouter.ai/api/v1/chat/completions"

    # VLM Retry
    VLM_MAX_RETRIES: int = field(
        default_factory=lambda: int(os.getenv("VLM_MAX_RETRIES", "5"))
    )
    VLM_BASE_DELAY: float = field(
        default_factory=lambda: float(os.getenv("VLM_BASE_DELAY", "1.0"))
    )

    # RabbitMQ
    RABBITMQ_HOST: str = field(
        default_factory=lambda: os.getenv("RABBITMQ_HOST", "localhost")
    )
    RABBITMQ_PORT: int = field(
        default_factory=lambda: int(os.getenv("RABBITMQ_PORT", "5672"))
    )
    RABBITMQ_USER: str = field(
        default_factory=lambda: os.getenv("RABBITMQ_USER", "guest")
    )
    RABBITMQ_PASSWORD: str = field(
        default_factory=lambda: os.getenv("RABBITMQ_PASSWORD", "guest")
    )
    RABBITMQ_QUEUE: str = field(
        default_factory=lambda: os.getenv("RABBITMQ_QUEUE", "image_processing")
    )

    # Paths (lazy -- only create on access)
    @property
    def OUTPUTS_DIR(self) -> Path:
        return _ensure_dir(self.BASE_DIR / "outputs")

    @property
    def UPLOAD_DIR(self) -> Path:
        return _ensure_dir(self.BASE_DIR / "uploads")

    def validate(self) -> None:
        """Raise ValueError if config is invalid."""
        if (
            not self.OPENROUTER_API_KEY
            or self.OPENROUTER_API_KEY == "your_openrouter_api_key_here"
        ):
            raise ValueError(
                "OPENROUTER_API_KEY chua duoc thiet lap hoac khong hop le."
            )
        if not (1 <= self.RABBITMQ_PORT <= 65535):
            raise ValueError(f"RABBITMQ_PORT khong hop le: {self.RABBITMQ_PORT}")


settings = Settings()
