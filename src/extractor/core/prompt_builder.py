"""Prompt construction logic for VLM extraction."""


def _format_manifest(manifest: list[dict] | None) -> str:
    """Render the page->file manifest so the model can attribute each page."""
    if not manifest:
        return ""

    mode_label = {"text": "text", "image": "anh", "mixed": "text+anh"}
    lines = []
    for entry in manifest:
        rng = (
            f"trang {entry['page_start']}"
            if entry["page_start"] == entry["page_end"]
            else f"trang {entry['page_start']}-{entry['page_end']}"
        )
        mode = mode_label.get(entry.get("mode", ""), entry.get("mode", ""))
        lines.append(f'- {rng}: "{entry["file"]}" ({entry.get("type", "")}, dang {mode})')

    return (
        "\nDANH SACH FILE NGUON (cac trang duoi day xep theo dung thu tu nay; "
        "moi trang la TEXT trich tu PDF hoac ANH):\n" + "\n".join(lines) + "\n"
    )


def build_extraction_prompt(
    template_str: str,
    error_context: str = "",
    manifest: list[dict] | None = None,
) -> str:
    """Build the VLM prompt for SPARSE extraction.

    ``template_str`` is the comprehensive template shown so the model knows the
    group keys, each test's ``stt``/``name`` and reference values. To minimise
    output (-> faster), the model returns ONLY the data it found (sparse), keyed
    back to the template; the code merges it into the full template afterwards.
    All pages belong to the SAME patient (mixed PDF + image); ``manifest`` maps
    each page to its file so the model reads every slip and merges them.
    """
    error_instruction = ""
    if error_context:
        error_instruction = f"""
LOI LAN TRUOC: {error_context}
Hay tra lai JSON SPARSE dung dinh dang mo ta o duoi.
"""

    manifest_block = _format_manifest(manifest)

    return f"""
Ban la tro ly y te chuyen doc cac phieu ket qua xet nghiem / can lam sang.

Ban se nhan duoc NHIEU trang (text trich tu PDF va/hoac anh) thuoc CUNG MOT
BENH NHAN. Moi file co the la mot phieu RIENG cua mot KHOA khac nhau (Huyet hoc,
Vi sinh, Mien dich, Sinh hoa, Dong mau, Chan doan hinh anh...). DOC KY tat ca.
{manifest_block}
TEMPLATE THAM CHIEU (chi de tra cuu key nhom, `stt`/`name` cua test, khoang
tham chieu - DUNG chep lai template nay vao ket qua):
{template_str}

CACH TRA VE (QUAN TRONG - tra ve SPARSE, chi nhung gi TIM DUOC):
- KHONG chep lai `name`, `reference_range`, `unit` (da co san trong template).
- KHONG xuat cac truong/test/nhom khong co du lieu.
- Tra ve DUNG cau truc JSON sau (bo qua phan rong):
{{
  "document": {{ <chi field co gia tri, vd "record_number": "...", "priority": "..."> }},
  "patient":  {{ <chi field co gia tri, vd "full_name": "...", "year_of_birth": 1960> }},
  "groups": {{
    "<group_key chinh xac tu template>": {{
      "department": "...", "time_collected": "...", "time_resulted": "...",
      "metadata": {{ <chi field metadata co gia tri> }},
      "tests": [
        {{ "stt": <so stt cua test>, "value": ..., "flag": "H/L/null",
           "note": "...", "process_code": "...", "device": "..." }},
        {{ "stt": <stt cua test cha co sub_tests>,
           "sub_tests": [ {{ "name": "PT-RP(s)", "value": 10.3, "flag": null }} ] }}
      ]
    }}
  }},
  "imaging_and_functional": {{
    "<exam_key chinh xac>": {{ "result": "...", "note": "...", "source_type": "pdf/image" }}
  }},
  "_unrecognized_sources": [ {{ "file": "...", "reason": "..." }} ]
}}

QUY TAC:
1. Moi test tham chieu bang `stt` (so thu tu trong template cua nhom do); rieng
   cac sub_test thi tham chieu bang `name`. KHONG bia stt; chi dung stt co thuc.
2. KHAI THAC TOI DA tu CA anh lan PDF: value, flag, note (Ghi chu), process_code
   (Quy trinh XN), device (Thiet bi); va metadata cua phieu (nguoi lay/nhan mau,
   loai mau, tinh trang mau, so phieu, barcode, thoi gian duyet/in, bac si, chu
   nhiem khoa, nhan xet, ...).
3. UU TIEN DU LIEU MOI NHAT: neu mot gia tri co o CA anh va PDF -> lay tu PDF.
   Dat `metadata.source_type` = "pdf" hoac "image" cho moi nhom co du lieu.
4. `flag`: "H" (cao), "L" (thap) hoac null (tu so sanh voi khoang tham chieu).
5. KHONG BIA DU LIEU: file/trang KHONG phai phieu xet nghiem hoac khong khop
   template -> dua ten file vao `_unrecognized_sources` KEM LY DO, khong dien gi.
   Neu tat ca hop le thi `_unrecognized_sources`: [].
6. CHI tra ve JSON hop le, KHONG boc trong ```json```.
{error_instruction}
""".strip()
