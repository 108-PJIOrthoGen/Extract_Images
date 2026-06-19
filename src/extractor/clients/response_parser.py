"""Helpers for cleaning raw VLM text responses before JSON parsing."""

import re

_LEADING_FENCE_RE = re.compile(r"^```[a-zA-Z]*\n")
_TRAILING_FENCE_RE = re.compile(r"```$")


def clean_markdown_response(text: str) -> str:
    """Strip a leading/trailing markdown code fence from a model response.

    Some providers wrap JSON in ```json ... ``` despite being asked not to; this
    removes the fence so the payload can be parsed directly.
    """
    text = _LEADING_FENCE_RE.sub("", text)
    text = _TRAILING_FENCE_RE.sub("", text.strip())
    return text.strip()
