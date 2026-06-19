"""Extraction pipeline orchestrator."""

import json
import time

from extractor.clients.vlm_client import OpenRouterVLMClient
from extractor.config import settings
from extractor.core import schema_keys as keys
from extractor.core.completeness import build_extraction_meta
from extractor.core.prompt_builder import build_extraction_prompt
from extractor.core.sparse_merge import merge_sparse_into_template
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

    def extract(
        self,
        template_str: str,
        content_parts: list[dict],
        manifest: list[dict] | None = None,
    ) -> str:
        """Run extraction pipeline (SPARSE) with validation and retry.

        ``template_str`` is the comprehensive template shown to the VLM for
        reference. The VLM returns ONLY the data it found (sparse), which is then
        merged onto a full copy of the template -> the output still contains every
        field. ``content_parts`` are the mixed text/image pages. ``manifest`` maps
        each page to its source file so the model reads every uploaded slip
        (PDF + image) and merges them for the one patient.
        """
        template = json.loads(template_str)
        logger.info(f"Bat dau trich xuat (sparse) tu {len(content_parts)} trang (text/anh)")

        last_error = ""
        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"Attempt {attempt + 1}/{self.max_retries + 1}: Goi VLM...")
                prompt = build_extraction_prompt(template_str, last_error, manifest)
                response_text = self.client.call(prompt, content_parts)

                try:
                    sparse = json.loads(response_text)
                except json.JSONDecodeError as e:
                    last_error = f"JSON parse error: {e}. Response: {response_text[:200]}"
                    logger.warning(f"Attempt {attempt + 1} - {last_error}")
                    if attempt < self.max_retries:
                        continue
                    raise ValidationError(f"Invalid JSON after {attempt + 1} attempts: {e}") from e

                if not isinstance(sparse, dict) or not any(
                    k in sparse for k in keys.SPARSE_TOP_LEVEL_KEYS
                ):
                    last_error = "Response khong dung dinh dang sparse mong doi."
                    logger.warning(f"Attempt {attempt + 1} - {last_error}")
                    if attempt < self.max_retries:
                        continue
                    raise ValidationError(f"Bad sparse shape after {attempt + 1} attempts.")

                # The VLM may flag uploaded files that are NOT lab results / do
                # not match the template; surface that under extraction_meta.
                unrecognized = sparse.pop(keys.SPARSE_UNRECOGNIZED, None)

                # Merge the sparse payload onto the full template so the output
                # keeps every field (missing ones stay null/"").
                result = merge_sparse_into_template(template, sparse)

                meta = build_extraction_meta(
                    result,
                    manifest,
                    unrecognized,
                    settings.LOW_FILL_RATE_THRESHOLD,
                )
                result[keys.EXTRACTION_META] = meta

                c = meta["completeness"]
                logger.info(
                    "Merge thanh cong | fill_rate=%s | usable=%s | "
                    "low_fill=%s | empty_groups=%s | warnings=%s",
                    c["fill_rate"],
                    c["has_usable_data"],
                    c["low_fill_rate"],
                    c["empty_groups"] or "none",
                    meta["warnings"] or "none",
                )
                return json.dumps(result, indent=2, ensure_ascii=False)

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
