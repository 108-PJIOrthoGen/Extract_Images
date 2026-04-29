"""Response validation logic for VLM extraction."""

import json
from typing import Any


def extract_keys(obj: Any, prefix: str = "") -> set[str]:
    """Recursively extract all keys from nested object."""
    keys = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            full_key = f"{prefix}.{k}" if prefix else k
            keys.add(full_key)
            if isinstance(v, dict):
                keys.update(extract_keys(v, full_key))
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        keys.update(extract_keys(item, full_key))
    return keys


def validate_response(template_str: str, response_json: dict) -> list[str]:
    """Validate response has all required fields from template.

    Returns:
        List of error messages. Empty list if valid.
    """
    template_keys = extract_keys(json.loads(template_str))
    response_keys = extract_keys(response_json)
    missing_keys = template_keys - response_keys

    if not missing_keys:
        return []

    missing_list = sorted(list(missing_keys)[:10])
    if len(missing_keys) > 10:
        missing_list.append(f"...va {len(missing_keys) - 10} truong khac")
    return [f"Thieu cac truong: {', '.join(missing_list)}"]


def clean_markdown_response(text: str) -> str:
    """Clean markdown blocks from VLM response."""
    import re

    text = re.sub(r"^```[a-zA-Z]*\n", "", text)
    text = re.sub(r"```$", "", text.strip())
    return text
