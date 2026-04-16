import base64
from pathlib import Path
from typing import List

from extractor.utils.logger import logger

def get_base64_image(image_path: Path) -> str:
    """
    Đọc tệp hình ảnh và mã hoá thành chuỗi Base64 cùng với MIME type.
    
    Args:
        image_path (Path): Đường dẫn tới tệp hình ảnh.
        
    Returns:
        str: Chuỗi hình ảnh đã mã hoá kèm prefix chuẩn data URL (vd: data:image/jpeg;base64,...)
    """
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found at: {image_path}")
        
    ext = image_path.suffix.lower()
    if ext == ".png":
        mime_type = "image/png"
    elif ext in [".jpg", ".jpeg"]:
        mime_type = "image/jpeg"
    else:
        # Default fallback
        mime_type = "image/jpeg"
        logger.warning(f"Unknown extension {ext} for {image_path}, defaulting to image/jpeg")
        
    try:
        encoded_string = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        return f"data:{mime_type};base64,{encoded_string}"
    except Exception as e:
        logger.error(f"Error reading and encoding image {image_path}: {e}")
        raise

def load_images_from_directory(directory_path: Path) -> List[str]:
    """
    Quét tất cả ảnh (.png, .jpg, .jpeg) trong một thư mục và chuyển chúng sang Base64 str.
    
    Args:
        directory_path (Path): Đường dẫn tới thư mục chứa ảnh.
        
    Returns:
        List[str]: Danh sách các chuỗi base64 của ảnh.
    """
    images_base64 = []
    if not directory_path.exists() or not directory_path.is_dir():
        logger.warning(f"Directory not found or invalid: {directory_path}")
        return images_base64
        
    # Sắp xếp theo tên để đảm bảo thứ tự các trang
    for item in sorted(directory_path.iterdir()):
        if item.is_file() and item.suffix.lower() in ('.png', '.jpg', '.jpeg'):
            logger.info(f"Đang phân tích hình ảnh: {item.name}")
            b64 = get_base64_image(item)
            images_base64.append(b64)
            
    return images_base64
