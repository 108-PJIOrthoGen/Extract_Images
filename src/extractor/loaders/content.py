"""Helpers for building OpenRouter/VLM message *content parts*.

A "content part" is one element of a chat message's ``content`` list. We support
two kinds so the pipeline can mix extracted PDF text with rendered/photo images
in a single request:

- text part:  {"type": "text", "text": "..."}
- image part: {"type": "image_url", "image_url": {"url": "data:image/...;base64,..."}}
"""


def text_part(text: str) -> dict:
    """Build a text content part."""
    return {"type": "text", "text": text}


def image_part(data_url: str) -> dict:
    """Build an image content part from a base64 data URL."""
    return {"type": "image_url", "image_url": {"url": data_url}}


def part_kind(part: dict) -> str:
    """Return "text" or "image" for a content part."""
    return "text" if part.get("type") == "text" else "image"
