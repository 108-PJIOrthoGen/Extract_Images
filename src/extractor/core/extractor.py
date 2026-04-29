"""Extraction pipeline orchestrator."""

import json
import time

from extractor.clients.vlm_client import OpenRouterVLMClient
from extractor.core.prompt_builder import build_extraction_prompt
from extractor.core.response_validator import (
    extract_keys,
    validate_response,
)
from extractor.exceptions import ValidationError, VLMRateLimitError
from extractor.utils.logger import setup_logger

logger = setup_logger(__name__)


class ExtractionPipeline:
    """Orchestrates the full extraction workflow: prompt -> call -> validate -> retry."""

    def __init__(
        self,
        client: OpenRouterVLMClient,
        max_retries: int = 5,
        base_delay: float = 1.0,
    ):
        self.client = client
        self.max_retries = max_retries
        self.base_delay = base_delay

    def extract(self, template_str: str, base64_images: list[str]) -> str:
        """Run extraction pipeline with validation and retry."""
        template_key_count = len(extract_keys(json.loads(template_str)))
        logger.info(f"Template co {template_key_count} keys can validate")

        last_error = ""
        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"Attempt {attempt + 1}/{self.max_retries + 1}: Goi VLM...")
                prompt = build_extraction_prompt(template_str, last_error)
                response_text = self.client.call(prompt, base64_images)

                try:
                    response_json = json.loads(response_text)
                except json.JSONDecodeError as e:
                    last_error = f"JSON parse error: {e}. Response: {response_text[:200]}"
                    logger.warning(f"Attempt {attempt + 1} - {last_error}")
                    if attempt < self.max_retries:
                        continue
                    raise ValidationError(f"Invalid JSON after {attempt + 1} attempts: {e}") from e

                errors = validate_response(template_str, response_json)
                if errors:
                    last_error = errors[0]
                    logger.warning(f"Attempt {attempt + 1} - Thieu truong: {last_error}")
                    if attempt < self.max_retries:
                        continue
                    raise ValidationError(
                        f"Missing fields after {attempt + 1} attempts: {last_error}"
                    )

                logger.info("Validation thanh cong")
                return json.dumps(response_json, indent=2, ensure_ascii=False)

            except VLMRateLimitError:
                if attempt < self.max_retries:
                    wait = self.base_delay * (2**attempt) + 0.1 * attempt
                    logger.warning(f"Rate limited. Retry {attempt + 1} in {wait:.1f}s...")
                    time.sleep(wait)
                    continue
                raise

            except ValidationError:
                if attempt >= self.max_retries:
                    raise
                continue

        raise ValidationError(
            f"Failed after {self.max_retries + 1} attempts. Last error: {last_error}"
        )
