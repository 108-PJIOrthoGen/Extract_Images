import argparse
import sys
from pathlib import Path

from extractor.config import TEMPLATE_PATH, OUTPUTS_DIR
from extractor.core.template_parser import load_template_schema
from extractor.core.image_loader import load_images_from_directory
from extractor.core.vlm_client import OpenRouterVLMClient
from extractor.utils.logger import logger

def main():
    parser = argparse.ArgumentParser(description="Medical Image Data Extractor using OpenRouter VLM.")
    parser.add_argument(
        "--input", 
        default="images/test_case_01", 
        help="Thư mục đầu vào chứa các hình ảnh cần trích xuất."
    )
    args = parser.parse_args()

    input_dir = Path(args.input)
    if not input_dir.exists() or not input_dir.is_dir():
        logger.error(f"Thư mục đầu vào không hợp lệ hoặc không tồn tại: {input_dir}")
        sys.exit(1)

    # Xác định tên file đầu ra dựa trên tên thư mục đầu vào
    input_basename = input_dir.name if input_dir.name else "extracted_results"
    
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUTS_DIR / f"{input_basename}.json"

    logger.info("Bước 1: Nạp Schema Template...")
    try:
        template_str = load_template_schema(TEMPLATE_PATH)
    except Exception as e:
        logger.error(f"Thất bại khi nạp template: {e}")
        sys.exit(1)

    logger.info(f"Bước 2: Nạp Hình Ảnh từ {input_dir}...")
    images_base64 = load_images_from_directory(input_dir)
    
    if not images_base64:
        logger.warning("Không tìm thấy hình ảnh nào để xử lý. Dừng chương trình.")
        sys.exit(0)

    logger.info(f"Đã nạp {len(images_base64)} hình ảnh hợp lệ.")
    logger.info("Bước 3: Gọi OpenRouter VLM để xử lý...")
    
    try:
        client = OpenRouterVLMClient()
        extracted_info = client.extract_data(template_str, images_base64)
        
        # Ghi kết quả
        output_path.write_text(extracted_info, encoding="utf-8")
        logger.info(f"Thành công! Dữ liệu đã được lưu tại: {output_path}")
        
    except Exception as e:
        logger.error(f"Thất bại trong quá trình gọi VLM hoặc ghi file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
