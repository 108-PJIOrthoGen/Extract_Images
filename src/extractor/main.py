"""CLI entry point for medical image data extraction."""

import argparse
import sys
from pathlib import Path

from extractor.clients.vlm_client import OpenRouterVLMClient
from extractor.config import settings
from extractor.core.extractor import ExtractionPipeline
from extractor.core.template_parser import load_template_schema
from extractor.loaders.image_loader import load_images_from_directory
from extractor.utils.logger import setup_logger

logger = setup_logger(__name__)


def main():
    """Run the extraction pipeline from CLI."""
    parser = argparse.ArgumentParser(
        description="Medical Image Data Extractor using OpenRouter VLM."
    )
    parser.add_argument(
        "--input",
        default="images/test_case_01",
        help="Thu muc dau vao chua cac hinh anh can trich xuat.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Duong dan file JSON dau ra (mac dinh: outputs/<ten_thu_muc>.json)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override model VLM (vd: openai/gpt-4o)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=None,
        help="Override so lan retry toi da",
    )
    args = parser.parse_args()

    # Validate config
    try:
        settings.validate()
    except ValueError as e:
        logger.error(f"Config error: {e}")
        sys.exit(1)

    input_dir = Path(args.input)
    if not input_dir.exists() or not input_dir.is_dir():
        logger.error(
            f"Thu muc dau vao khong hop le hoac khong ton tai: {input_dir}"
        )
        sys.exit(1)

    output_path = (
        Path(args.output)
        if args.output
        else settings.OUTPUTS_DIR / f"{input_dir.name}.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Buoc 1: Nap Schema Template...")
    try:
        template_str = load_template_schema(settings.TEMPLATE_PATH)
    except Exception as e:
        logger.error(f"That bai khi nap template: {e}")
        sys.exit(1)

    logger.info(f"Buoc 2: Nap Hinh Anh tu {input_dir}...")
    images_base64 = load_images_from_directory(input_dir)

    if not images_base64:
        logger.warning("Khong tim thay hinh anh nao de xu ly. Dung chuong trinh.")
        sys.exit(0)

    logger.info(f"Da nap {len(images_base64)} hinh anh hop le.")
    logger.info("Buoc 3: Goi OpenRouter VLM de xu ly...")

    try:
        client = OpenRouterVLMClient(model=args.model)
        pipeline = ExtractionPipeline(
            client=client,
            max_retries=args.max_retries or settings.VLM_MAX_RETRIES,
        )
        extracted_info = pipeline.extract(template_str, images_base64)

        output_path.write_text(extracted_info, encoding="utf-8")
        logger.info(f"Thanh cong! Du lieu da duoc luu tai: {output_path}")

    except Exception as e:
        logger.error(f"That bai trong qua trinh goi VLM hoac ghi file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
