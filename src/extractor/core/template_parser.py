"""Template parsing utilities (fail-fast on malformed JSON)."""

import json
from pathlib import Path

from extractor.exceptions import TemplateError
from extractor.utils.logger import setup_logger

logger = setup_logger(__name__)


def load_template_schema(template_path: Path) -> str:
    """Read the JSON template, validate it, and return a normalized string.

    The template is medical reference data: if a hospital hand-edits it and
    breaks the JSON, we fail fast with a precise error (line/column) rather than
    silently "fixing" it -- a regex patch could corrupt valid values and feed the
    VLM a wrong schema. The worker turns :class:`TemplateError` into
    ``status="failed"`` so ops can correct the file.

    Args:
        template_path: Path to the template schema file.

    Returns:
        Standardized (prettified, validated) JSON string ready for model context.
    """
    if not template_path.exists():
        logger.error(f"Template schema not found at: {template_path}")
        raise FileNotFoundError(f"Template schema not found at: {template_path}")

    content = template_path.read_text(encoding="utf-8")

    try:
        # Load and dump again to ensure it is 100% valid JSON and prettified.
        data = json.loads(content)
    except json.JSONDecodeError as e:
        # Fallback for a hospital that edits template.json and breaks it: fail
        # fast with a clear error instead of feeding raw text to the VLM (which
        # would produce confusing downstream failures). The worker turns this
        # into status="failed" with this message so ops can fix the template.
        logger.error(f"Template JSON khong hop le: {e}")
        raise TemplateError(
            f"Template JSON khong hop le tai {template_path} (dong {e.lineno}, "
            f"cot {e.colno}): {e.msg}. Hay kiem tra lai cau truc template.json."
        ) from e

    if not isinstance(data, dict) or not data:
        raise TemplateError(f"Template tai {template_path} phai la mot JSON object khong rong.")
    return json.dumps(data, indent=2, ensure_ascii=False)
