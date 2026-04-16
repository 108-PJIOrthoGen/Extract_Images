import json
import re
from pathlib import Path

from extractor.utils.logger import logger

def fix_malformed_json(content: str) -> str:
    """
    Sửa chữa nhanh các chuỗi JSON được chỉnh sửa thủ công có thể chứa lỗi cú pháp 
    (chẳng hạn thiếu value, thừa phẩy). Thay thế các giá trị rỗng/thiếu bằng chuỗi placeholder.
    
    Args:
        content (str): Chuỗi JSON văn bản thô.
        
    Returns:
        str: Chuỗi JSON đã được làm sạch và chèn "__FILL_ME__".
    """
    # Thay thế các trường hợp như "key": , thành "key": "__FILL_ME__",
    fixed = re.sub(r':\s*,', ': "__FILL_ME__",', content)
    # Thay thế các trường hợp value bị thiếu trước dòng mới vd "key": \n
    fixed = re.sub(r':\s*\n', ': "__FILL_ME__"\n', fixed)
    # Thay thế các trường hợp value bị thiếu trước ngoặc nhọn vd "key": }
    fixed = re.sub(r':\s*}', ': "__FILL_ME__"}', fixed)
    return fixed

def load_template_schema(template_path: Path) -> str:
    """
    Đọc template JSON từ file, gọi hàm chuẩn hoá để sửa file lỗi do chỉnh sửa bằng tay,
    và trả về định dạng string chuẩn hoá (format đẹp).
    
    Args:
        template_path (Path): Đường dẫn tới file Schema.
        
    Returns:
        str: Chuỗi String JSON nguyên vẹn chuẩn bị được đưa vào context model.
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
        logger.error(f"Lỗi cú pháp khi phân tích fixed template JSON: {e}")
        logger.warning("Vẫn tiếp tục trả về chuỗi text thô mặc dù không phải chuẩn JSON.")
        return fixed_content
