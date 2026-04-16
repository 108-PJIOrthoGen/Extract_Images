import json
import re
from typing import List
import requests

from extractor.config import OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_API_URL
from extractor.utils.logger import logger

class OpenRouterVLMClient:
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or OPENROUTER_API_KEY
        self.model = model or OPENROUTER_MODEL
        self.url = OPENROUTER_API_URL
        
        if not self.api_key or self.api_key == "your_openrouter_api_key_here":
            raise ValueError("Vui lòng thiết lập biến môi trường OPENROUTER_API_KEY hợp lệ.")

    def _build_prompt(self, template_str: str) -> str:
        """Tạo prompt hệ thống điều hướng VLM."""
        return f"""
Bạn là một trợ lý y tế chuyên phân tích hình ảnh và trích xuất dữ liệu.
Nhiệm vụ của bạn là xem các hình ảnh kết quả xét nghiệm/y tế và điền thông tin vào một cấu trúc JSON có sẵn.

Cấu trúc JSON template nằm ở dưới. 
YÊU CẦU:
1. Bạn CHỈ được điền dữ liệu vào các trường có giá trị là chuỗi rỗng `""` hoặc placeholder có giá trị `"__FILL_ME__"`.
2. Đối với các trường đã có sẵn dữ liệu hoặc mang giá trị `null`, BẠN PHẢI GIỮ NGUYÊN và KHÔNG ĐƯỢC THAY ĐỔI so với template được cấp.
3. Chỉ trả về một JSON object hợp lệ, không bọc trong markdown block như ```json hay chứa thêm bất kỳ bình luận nào.
4. Thông tin bạn lấy phải hoàn toàn dựa trên hình ảnh được cấp. Nếu hình ảnh không có thông tin để điền, hãy để nguyên là null hoặc "".

Tạo JSON với chính cấu trúc như sau:
{template_str}
"""

    def _clean_markdown_response(self, text: str) -> str:
        """Làm sạch các markdown blocks dư thừa trả về từ model."""
        text = re.sub(r'^```[a-zA-Z]*\n', '', text)
        text = re.sub(r'```$', '', text.strip())
        return text

    def extract_data(self, template_str: str, base64_images: List[str]) -> str:
        """
        Gọi OpenRouter API cùng với hình ảnh để trích xuất dữ liệu JSON.
        
        Args:
            template_str (str): Khuôn mẫu Data Schema định dạng text JSON.
            base64_images (List[str]): Danh sách các base64 text của ảnh.
            
        Returns:
            str: Data JSON chứa thông tin trích xuất.
        """
        prompt = self._build_prompt(template_str)
        content_list = [{"type": "text", "text": prompt}]
        
        for b64 in base64_images:
            content_list.append({
                "type": "image_url",
                "image_url": {"url": b64}
            })
            
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": content_list}],
            "temperature": 0.0  # Tối ưu hoá tính trung thực/chính xác
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"Đang gửi request trích xuất tới OpenRouter. Model: {self.model}")
        
        try:
            response = requests.post(self.url, headers=headers, json=payload)
            response.raise_for_status()
            
            result_json = response.json()
            message_content = result_json["choices"][0]["message"]["content"]
            
            return self._clean_markdown_response(message_content)
            
        except requests.exceptions.HTTPError as he:
            logger.error(f"OpenRouter API HTTP Error: {he}")
            if hasattr(he, 'response') and he.response is not None:
                logger.error(f"Response data: {he.response.text}")
            raise
        except Exception as e:
            logger.error(f"Đã xảy ra lỗi không xác định khi gọi API: {e}")
            raise
