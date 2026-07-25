"""Document loading utilities.

Handles both images and PDFs. Every input is normalized into a list of VLM
*content parts* (text and/or image) so the rest of the pipeline stays
modality-blind:

- an image file  -> one image part
- a PDF (hybrid) -> one part per page: text part if the page has a text layer,
  otherwise a rendered image part
"""

import base64
from pathlib import Path

from extractor.loaders.constants import (
    IMAGE_EXTENSIONS,
    MIME_MAP,
    PDF_EXTENSIONS,
    SUPPORTED_EXTENSIONS,
)
from extractor.loaders.content import image_part, part_kind
from extractor.loaders.pdf_loader import load_pdf_parts
from extractor.utils.logger import setup_logger

logger = setup_logger(__name__)


def get_base64_image(image_path: Path) -> str:
    """Read an image file and encode it as a Base64 data URL.

    Args:
        image_path: Path to image file.

    Returns:
        Base64 encoded image with a ``data:`` URL prefix.
    """
    if isinstance(image_path, str):
        image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(f"Image not found at: {image_path}")

    ext = image_path.suffix.lower()
    mime_type = MIME_MAP.get(ext, "image/jpeg")
    if ext not in MIME_MAP:
        logger.warning(f"Unknown extension {ext} for {image_path}, defaulting to image/jpeg")

    try:
        encoded = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"
    except Exception as e:
        logger.error(f"Error reading and encoding image {image_path}: {e}")
        raise


def load_file_to_parts(file_path: Path) -> list[dict]:
    """Load a single file (image or PDF) into a list of VLM content parts.

    Images yield one image part; PDFs yield one part per page (text or image,
    hybrid). Unsupported files yield an empty list.

    Args:
        file_path: Path to an image or PDF file.

    Returns:
        List of content parts.
    """
    if isinstance(file_path, str):
        file_path = Path(file_path)

    ext = file_path.suffix.lower()
    if ext in PDF_EXTENSIONS:
        return load_pdf_parts(file_path)
    if ext in IMAGE_EXTENSIONS:
        logger.info(f"Dang phan tich hinh anh: {file_path.name}")
        return [image_part(get_base64_image(file_path))]

    logger.warning(f"Bo qua file khong ho tro: {file_path.name}")
    return []


def _file_type(ext: str) -> str:
    return "pdf" if ext in PDF_EXTENSIONS else "image"


def _manifest_mode(parts: list[dict]) -> str:
    """Summarize a file's parts as "text", "image", or "mixed"."""
    kinds = {part_kind(p) for p in parts}
    if kinds == {"text"}:
        return "text"
    if kinds == {"image"}:
        return "image"
    return "mixed"


def load_documents_with_manifest(
    paths: list[Path],
) -> tuple[list[dict], list[dict]]:
    """Load files into content parts plus a manifest mapping pages -> source file.

    The manifest lets the VLM (and us) know exactly which page belongs to which
    uploaded file, so multiple slips of one patient are extracted in full and
    never merged across departments. Each entry::

        {"file": "phieu_huyet_hoc.pdf", "type": "pdf", "mode": "text",
         "pages": 2, "page_start": 1, "page_end": 2}

    ``mode`` is how the pages were sent (text / image / mixed). page_start /
    page_end are 1-indexed positions in the flattened parts list.

    Args:
        paths: Ordered list of file paths (images and/or PDFs).

    Returns:
        Tuple of (flattened content parts, manifest list).
    """
    all_parts: list[dict] = []
    manifest: list[dict] = []

    for path in paths:
        if isinstance(path, str):
            path = Path(path)
        ext = path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            logger.warning(f"Bo qua file khong ho tro: {path.name}")
            continue

        parts = load_file_to_parts(path)
        if not parts:
            continue

        start = len(all_parts) + 1
        all_parts.extend(parts)
        manifest.append(
            {
                "file": path.name,
                "type": _file_type(ext),
                "mode": _manifest_mode(parts),
                "pages": len(parts),
                "page_start": start,
                "page_end": len(all_parts),
            }
        )

    return all_parts, manifest


def iter_supported_files(directory_path: Path) -> list[Path]:
    """Return supported image/PDF files in a directory, sorted by name.

    Sorting preserves page/slip order. An invalid/missing directory yields ``[]``.
    """
    if not directory_path.exists() or not directory_path.is_dir():
        logger.warning(f"Directory not found or invalid: {directory_path}")
        return []
    return [
        item
        for item in sorted(directory_path.iterdir())
        if item.is_file() and item.suffix.lower() in SUPPORTED_EXTENSIONS
    ]


def load_directory_with_manifest(
    directory_path: Path,
) -> tuple[list[dict], list[dict]]:
    """Like :func:`load_documents_with_manifest` but scans a directory (sorted)."""
    return load_documents_with_manifest(iter_supported_files(directory_path))
