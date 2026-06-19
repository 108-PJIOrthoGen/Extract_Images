"""PDF loading (hybrid).

For each PDF page we prefer the embedded text layer (born-digital reports give
clean, diacritic-correct Vietnamese text -- far better than OCR). A page with
too little extractable text (i.e. a scanned image) is rendered to an image and
sent to the VLM instead. The two kinds flow through the same request as mixed
content parts.
"""

import base64
from pathlib import Path

import fitz  # PyMuPDF

from extractor.config import settings
from extractor.loaders.content import image_part, text_part
from extractor.utils.logger import setup_logger

logger = setup_logger(__name__)


def _render_page_to_data_url(page: "fitz.Page", dpi: int) -> str:
    pix = page.get_pixmap(dpi=dpi)
    encoded = base64.b64encode(pix.tobytes("png")).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def load_pdf_parts(
    pdf_path: Path,
    dpi: int | None = None,
    text_min_chars: int | None = None,
) -> list[dict]:
    """Load a PDF into content parts, one per page (hybrid text/image).

    Args:
        pdf_path: Path to the PDF file.
        dpi: Render resolution for scanned pages (defaults to settings).
        text_min_chars: Min extractable chars to treat a page as text (defaults
            to settings.PDF_TEXT_MIN_CHARS).

    Returns:
        List of content parts (text and/or image) in page order.
    """
    if isinstance(pdf_path, str):
        pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found at: {pdf_path}")

    render_dpi = dpi or settings.PDF_RENDER_DPI
    threshold = text_min_chars if text_min_chars is not None else settings.PDF_TEXT_MIN_CHARS

    parts: list[dict] = []
    try:
        with fitz.open(pdf_path) as doc:
            n_text = n_img = 0
            for i, page in enumerate(doc):
                text = page.get_text("text").strip()
                if len(text) >= threshold:
                    parts.append(
                        text_part(
                            f'[Noi dung TEXT trang {i + 1} cua file "{pdf_path.name}"]\n{text}'
                        )
                    )
                    n_text += 1
                else:
                    parts.append(image_part(_render_page_to_data_url(page, render_dpi)))
                    n_img += 1
            logger.info(
                f"PDF {pdf_path.name}: {doc.page_count} trang "
                f"-> {n_text} text, {n_img} anh (@ {render_dpi}dpi)"
            )
    except Exception as e:
        logger.error(f"Error loading PDF {pdf_path}: {e}")
        raise

    return parts
