import logging
import sys

def setup_logger(name: str = "extractor") -> logging.Logger:
    """Cấu hình logger chuẩn cho toàn bộ project."""
    logger = logging.getLogger(name)
    
    # Chỉ cấu hình nếu logger chưa có handlers tránh duplicate logs
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
    return logger

# Tạo sẵn một instance logger chung
logger = setup_logger()
