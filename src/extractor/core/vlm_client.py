import json
import re
import time
from typing import List, Optional, Dict, Any
import requests

from extractor.config import (
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
    OPENROUTER_API_URL,
    VLM_MAX_RETRIES,
    VLM_BASE_DELAY,
)
from extractor.utils.logger import logger


class ValidationError(Exception):
    pass


class OpenRouterVLMClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: Optional[int] = None,
        base_delay: Optional[float] = None,
    ):
        self.api_key = api_key or OPENROUTER_API_KEY
        self.model = model or OPENROUTER_MODEL
        self.url = OPENROUTER_API_URL
        self.max_retries = max_retries if max_retries is not None else VLM_MAX_RETRIES
        self.base_delay = base_delay if base_delay is not None else VLM_BASE_DELAY

        if not self.api_key or self.api_key == "your_openrouter_api_key_here":
            raise ValueError("Vui lòng thiết lập biến môi trường OPENROUTER_API_KEY hợp lệ.")

    def _get_template_keys(self, template_str: str) -> set:
        """Trích xuất tất cả keys từ template để validate."""
        try:
            template = json.loads(template_str)
            return self._extract_keys(template)
        except json.JSONDecodeError:
            return set()

    def _extract_keys(self, obj: Any, prefix: str = "") -> set:
        """Đệ quy trích xuất tất cả keys từ nested object."""
        keys = set()
        if isinstance(obj, dict):
            for k, v in obj.items():
                full_key = f"{prefix}.{k}" if prefix else k
                keys.add(full_key)
                if isinstance(v, dict):
                    keys.update(self._extract_keys(v, full_key))
                elif isinstance(v, list):
                    for item in v:
                        if isinstance(item, dict):
                            keys.update(self._extract_keys(item, full_key))
        return keys

    def _validate_response(self, response_json: Dict, template_keys: set) -> List[str]:
        """Validate response có đủ trường như template không."""
        response_keys = self._extract_keys(response_json)
        missing_keys = template_keys - response_keys

        if missing_keys:
            missing_list = sorted(list(missing_keys)[:10])
            if len(missing_keys) > 10:
                missing_list.append(f"...và {len(missing_keys) - 10} trường khác")
            return [f"Thiếu các trường: {', '.join(missing_list)}"]
        return []

    def _build_prompt(self, template_str: str, error_context: str = "") -> str:
        """Tạo prompt hệ thống điều hướng VLM."""
        error_instruction = ""
        if error_context:
            error_instruction = f"""
LỖI LẦN TRƯỚC: {error_context}
Hãy trả lại JSON đầy đủ, đảm bảo tất cả các trường từ template đều có mặt.
"""

        return f"""
Bạn là một trợ lý y tế chuyên phân tích hình ảnh và trích xuất dữ liệu.
Nhiệm vụ của bạn là xem các hình ảnh kết quả xét nghiệm/y tế và điền thông tin vào một cấu trúc JSON có sẵn.

Cấu trúc JSON template nằm ở dưới. 
YÊU CẦU:
1. Bạn CHỈ được điền dữ liệu vào các trường có giá trị là chuỗi rỗng `""` hoặc placeholder có giá trị `"__FILL_ME__"`.
2. Đối với các trường đã có sẵn dữ liệu hoặc mang giá trị `null`, BẠN PHẢI GIỮ NGUYÊN và KHÔNG ĐƯỢC THAY ĐỔI so với template được cấp.
3. Chỉ trả về một JSON object hợp lệ, không bọc trong markdown block như ```json hay chứa thêm bất kỳ bình luận nào.
4. Thông tin bạn lấy phải hoàn toàn dựa trên hình ảnh được cấp. Nếu hình ảnh không có thông tin để điền, hãy để nguyên là null hoặc "".
5. QUAN TRỌNG: Đảm bảo JSON output có ĐẦY ĐỦ TẤT CẢ các keys từ template, không được bỏ sót bất kỳ trường nào.
{error_instruction}
Tạo JSON với chính cấu trúc như sau:
{template_str}
"""

    def _clean_markdown_response(self, text: str) -> str:
        """Làm sạch các markdown blocks dư thừa trả về từ model."""
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        text = re.sub(r"```$", "", text.strip())
        return text

    def _call_api(self, prompt: str, base64_images: List[str]) -> str:
        """Gọi OpenRouter API."""
        content_list = [{"type": "text", "text": prompt}]

        for b64 in base64_images:
            content_list.append({"type": "image_url", "image_url": {"url": b64}})

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": content_list}],
            "temperature": 0.0,
            "top_p": 1.0,
        }

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        response = requests.post(self.url, headers=headers, json=payload)
        response.raise_for_status()

        result_json = response.json()
        message_content = result_json["choices"][0]["message"]["content"]

        return self._clean_markdown_response(message_content)

    def extract_data(self, template_str: str, base64_images: List[str]) -> str:
        """
        Gọi OpenRouter API cùng với hình ảnh để trích xuất dữ liệu JSON.
        Có validation loop để đảm bảo đầy đủ trường.

        Args:
            template_str (str): Khuôn mẫu Data Schema định dạng text JSON.
            base64_images (List[str]): Danh sách các base64 text của ảnh.

        Returns:
            str: Data JSON chứa thông tin trích xuất.
        """
        template_keys = self._get_template_keys(template_str)
        logger.info(f"Template có {len(template_keys)} keys cần validate")

        last_error = ""

        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"Attempt {attempt + 1}/{self.max_retries + 1}: Gọi VLM...")

                prompt = self._build_prompt(template_str, last_error)
                response_text = self._call_api(prompt, base64_images)

                try:
                    response_json = json.loads(response_text)
                except json.JSONDecodeError as e:
                    last_error = f"JSON parse error: {e}. Response: {response_text[:200]}"
                    logger.warning(f"Attempt {attempt + 1} - {last_error}")
                    if attempt < self.max_retries:
                        continue
                    raise ValidationError(
                        f"Invalid JSON response after {attempt + 1} attempts: {e}"
                    )

                validation_errors = self._validate_response(response_json, template_keys)
                if validation_errors:
                    last_error = validation_errors[0]
                    logger.warning(f"Attempt {attempt + 1} - Thiếu trường: {last_error}")
                    if attempt < self.max_retries:
                        continue
                    raise ValidationError(
                        f"Missing fields after {attempt + 1} attempts: {last_error}"
                    )

                logger.info("Validation thành công - đầy đủ trường")
                return json.dumps(response_json, indent=2, ensure_ascii=False)

            except requests.exceptions.HTTPError as he:
                if he.response.status_code == 429 and attempt < self.max_retries:
                    wait_time = self.base_delay * (2**attempt) + (0.1 * attempt)
                    logger.warning(
                        f"Rate limited (429). Retry {attempt + 1}/{self.max_retries} in {wait_time:.1f}s..."
                    )
                    time.sleep(wait_time)
                    continue

                logger.error(f"OpenRouter API HTTP Error: {he}")
                if hasattr(he, "response") and he.response is not None:
                    logger.error(f"Response data: {he.response.text}")
                raise

            except ValidationError:
                if attempt >= self.max_retries:
                    raise
                continue

            except Exception as e:
                logger.error(f"Đã xảy ra lỗi không xác định khi gọi API: {e}")
                raise

        raise ValidationError(
            f"Failed after {self.max_retries + 1} attempts. Last error: {last_error}"
        )
