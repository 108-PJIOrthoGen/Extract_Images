"""Template parsing and JSON fixing utilities."""

import json
import re
from pathlib import Path

from extractor.utils.logger import setup_logger

logger = setup_logger(__name__)


def fix_malformed_json(content: str) -> str:
    """
    Quick fix for manually edited JSON strings that may contain syntax errors
    (e.g., missing values, extra commas). Replace empty/missing values with placeholder.

    Args:
        content: Raw JSON text string.

    Returns:
        Cleaned JSON string with "__FILL_ME__" inserted.
    """
    # Replace cases like "key": , with "key": "__FILL_ME__",
    fixed = re.sub(r':\s*,', ': "__FILL_ME__",', content)
    # Replace cases with missing value before newline, e.g., "key": \n
    fixed = re.sub(r':\s*\n', ': "__FILL_ME__"\n', fixed)
    # Replace cases with missing value before closing brace, e.g., "key": }
    fixed = re.sub(r':\s*}', ': "__FILL_ME__"}', fixed)
    return fixed


def load_template_schema(template_path: Path) -> str:
    """
    Read JSON template from file, normalize to fix manual editing errors,
    and return as formatted string.

    Args:
        template_path: Path to schema file.

    Returns:
        Standardized JSON string ready for model context.
    """
    if not template_path.exists():
        logger.error(f"Template schema not found at: {template_path}")
        raise FileNotFoundError(f"Template schema not found at: {template_path}")

    content = template_path.read_text(encoding="utf-8")
    fixed_content = fix_malformed_json(content)

    try:
        # Load and dump again to ensure it is 100% valid JSON and prettified
        data = json.loads(fixed_content)
        return json.dumps(data, indent=2, ensure_ascii=False)
    except json.JSONDecodeError as e:
        logger.error(f"Loi cu phap khi phan tich fixed template JSON: {e}")
        logger.warning("Van tiep tuc tra ve chuoi text tho mac du khong phai chuan JSON.")
        return fixed_content
