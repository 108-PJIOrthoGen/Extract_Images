"""Image loading and Base64 encoding utilities."""

import base64
from pathlib import Path

from extractor.utils.logger import setup_logger

logger = setup_logger(__name__)


SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}

MIME_MAP = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
}


def get_base64_image(image_path: Path) -> str:
    """
    Read image file and encode to Base64 string with MIME type.

    Args:
        image_path: Path to image file.

    Returns:
        Base64 encoded image with data URL prefix.
    """
    if isinstance(image_path, str):
        image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(f"Image not found at: {image_path}")

    ext = image_path.suffix.lower()
    mime_type = MIME_MAP.get(ext, "image/jpeg")
    if ext not in MIME_MAP:
        logger.warning(
            f"Unknown extension {ext} for {image_path}, defaulting to image/jpeg"
        )

    try:
        encoded = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"
    except Exception as e:
        logger.error(f"Error reading and encoding image {image_path}: {e}")
        raise


def load_images_from_directory(directory_path: Path) -> list[str]:
    """
    Scan all images in a directory and convert to Base64 strings.

    Args:
        directory_path: Path to directory containing images.

    Returns:
        List of base64 encoded image strings.
    """
    images_base64 = []
    if not directory_path.exists() or not directory_path.is_dir():
        logger.warning(f"Directory not found or invalid: {directory_path}")
        return images_base64

    # Sort by name to ensure page order
    for item in sorted(directory_path.iterdir()):
        if item.is_file() and item.suffix.lower() in SUPPORTED_EXTENSIONS:
            logger.info(f"Dang phan tich hinh anh: {item.name}")
            b64 = get_base64_image(item)
            images_base64.append(b64)

    return images_base64
