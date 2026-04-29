"""OpenRouter VLM client - API only."""

from typing import Any

import requests

from extractor.config import settings
from extractor.core.response_validator import clean_markdown_response
from extractor.exceptions import VLMAuthError, VLMClientError, VLMRateLimitError
from extractor.utils.logger import setup_logger

logger = setup_logger(__name__)


class OpenRouterVLMClient:
    """Responsible only for calling OpenRouter API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ):
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.model = model or settings.OPENROUTER_MODEL
        self.url = settings.OPENROUTER_API_URL

        if (
            not self.api_key
            or self.api_key == "your_openrouter_api_key_here"
        ):
            raise VLMAuthError(
                "OPENROUTER_API_KEY chua duoc thiet lap hoac khong hop le."
            )

    def call(self, prompt: str, base64_images: list[str]) -> str:
        """Send prompt + images to OpenRouter, return raw text response."""
        content_list: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        for b64 in base64_images:
            content_list.append(
                {"type": "image_url", "image_url": {"url": b64}}
            )

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": content_list}],
            "temperature": 0.0,
            "top_p": 1.0,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(self.url, headers=headers, json=payload)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if e.response is not None:
                if e.response.status_code == 401:
                    raise VLMAuthError(
                        f"Auth error: {e.response.text}"
                    ) from e
                if e.response.status_code == 429:
                    raise VLMRateLimitError(
                        f"Rate limited: {e.response.text}"
                    ) from e
            raise VLMClientError(f"HTTP Error: {e}") from e

        result = response.json()
        content = result["choices"][0]["message"]["content"]
        return clean_markdown_response(content)
