"""OpenRouter VLM client - API only."""

from typing import Any

import requests

from extractor.clients.response_parser import clean_markdown_response
from extractor.config import settings
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

        if not self.api_key or self.api_key == "your_openrouter_api_key_here":
            raise VLMAuthError("OPENROUTER_API_KEY chua duoc thiet lap hoac khong hop le.")

    def call(self, prompt: str, content_parts: list[dict[str, Any]]) -> str:
        """Send prompt + content parts (text and/or image) to OpenRouter.

        ``content_parts`` are pre-built message content parts (see
        ``extractor.loaders.content``): text parts for PDF text layers and
        image parts for photos / scanned pages.
        """
        content_list: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        content_list.extend(content_parts)

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": content_list}],
            "temperature": 0.0,
            "top_p": 1.0,
            "max_tokens": settings.VLM_MAX_TOKENS,
            "response_format": {"type": "json_object"},
        }
        # Route to the fastest provider serving this model (giảm delay của
        # OpenRouter). Bỏ trống OPENROUTER_PROVIDER_SORT để dùng routing mặc định.
        sort = settings.OPENROUTER_PROVIDER_SORT.strip()
        if sort:
            payload["provider"] = {"sort": sort}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        timeout = (settings.VLM_TIMEOUT_CONNECT, settings.VLM_TIMEOUT_READ)

        try:
            response = requests.post(self.url, headers=headers, json=payload, timeout=timeout)
            response.raise_for_status()
        except requests.exceptions.Timeout as e:
            raise VLMClientError(
                f"OpenRouter timeout sau {settings.VLM_TIMEOUT_READ}s "
                f"(model={self.model}). Thu lai hoac doi provider/model."
            ) from e
        except requests.exceptions.HTTPError as e:
            if e.response is not None:
                body = e.response.text
                status = e.response.status_code
                if status == 401:
                    raise VLMAuthError(f"Auth error: {body}") from e
                if status == 429:
                    raise VLMRateLimitError(f"Rate limited: {body}") from e
                raise VLMClientError(
                    f"HTTP {status} from OpenRouter (model={self.model}): {body}"
                ) from e
            raise VLMClientError(f"HTTP Error: {e}") from e

        result = response.json()
        content = result["choices"][0]["message"]["content"]
        return clean_markdown_response(content)
