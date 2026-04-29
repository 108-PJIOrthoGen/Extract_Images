from extractor.core.template_parser import fix_malformed_json


def test_fix_malformed_json_trailing_comma():
    # Trường hợp thiếu value do thừa phẩy
    malformed = '{"ho_ten": ,"tuoi": 25}'
    fixed = fix_malformed_json(malformed)
    assert fixed == '{"ho_ten": "__FILL_ME__","tuoi": 25}'

def test_fix_malformed_json_newline():
    # Trường hợp thiếu value và ngắt dòng
    malformed = '{"gioi_tinh": \n"id": 1}'
    fixed = fix_malformed_json(malformed)
    assert fixed == '{"gioi_tinh": "__FILL_ME__"\n"id": 1}'

def test_fix_malformed_json_brace_end():
    # Trường hợp thiếu value đóng ngoặc
    malformed = '{"ket_luan": }'
    fixed = fix_malformed_json(malformed)
    assert fixed == '{"ket_luan": "__FILL_ME__"}'
