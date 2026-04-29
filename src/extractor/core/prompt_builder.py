"""Prompt construction logic for VLM extraction."""


def build_extraction_prompt(template_str: str, error_context: str = "") -> str:
    """Build VLM prompt from template and optional error context."""
    error_instruction = ""
    if error_context:
        error_instruction = f"""
LOI LAN TRUOC: {error_context}
Hay tra lai JSON day du, dam bao tat ca cac truong tu template deu co mat.
"""

    return f"""
Ban la mot tro ly y te chuyen phan tich hinh anh va trich xuat du lieu.
Nhiem vu cua ban la xem cac hinh anh ket qua xet nghiem/y te
va dien thong tin vao mot cau truc JSON co san.

Cau truc JSON template nam o duoi.
YEU CAU:
1. Ban CHI duoc dien du lieu vao cac truong co gia tri la chuoi rong
   `""` hoac placeholder `"__FILL_ME__"`.
2. Doi voi cac truong da co du lieu hoac `null`, BAN PHAI GIU NGUYEN.
3. Chi tra ve JSON hop le, KHONG boc trong ```json```.
4. Thong tin chi lay tu hinh anh. Neu khong co, de null hoac "".
5. Dam bao JSON output DAY DU TAT CA keys tu template.
{error_instruction}
Tao JSON voi cau truc:
{template_str}
"""
