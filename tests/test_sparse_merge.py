import copy

from extractor.core.sparse_merge import (
    compute_abnormal_summary,
    merge_sparse_into_template,
)


def _template():
    return {
        "document": {"title": "X", "record_number": "", "priority": ""},
        "patient": {"full_name": "", "year_of_birth": None},
        "test_results": {
            "section_1_xet_nghiem": {
                "group_a_cbc": {
                    "department": "",
                    "time_collected": "",
                    "metadata": {"source_type": "", "sample_collector": "", "remarks": ""},
                    "tests": [
                        {
                            "stt": 2,
                            "name": "WBC",
                            "value": None,
                            "flag": None,
                            "reference_range": "4 - 10",
                            "unit": "G/L",
                            "note": None,
                            "process_code": None,
                            "device": None,
                        },
                        {
                            "stt": 3,
                            "name": "HGB",
                            "value": None,
                            "flag": None,
                            "reference_range": "120 - 150",
                            "unit": "g/L",
                            "note": None,
                            "process_code": None,
                            "device": None,
                        },
                    ],
                },
                "group_b_coag": {
                    "department": "",
                    "metadata": {"source_type": ""},
                    "tests": [
                        {
                            "stt": 1,
                            "category": "PT",
                            "sub_tests": [
                                {
                                    "name": "PT-RP(s)",
                                    "value": None,
                                    "flag": None,
                                    "reference_range": "10 - 14",
                                    "unit": "Giây",
                                },
                            ],
                        },
                    ],
                },
                "group_c_vi_sinh": {
                    "tests": [
                        {
                            "stt": 1,
                            "name": "Vi khuẩn nuôi cấy",
                            "value": "",
                            "flag": None,
                            "reference_range": None,
                            "unit": None,
                        },
                    ],
                },
            },
            "section_2_chan_doan_hinh_anh": {
                "exam_xray": {"name": "", "result": "", "note": "", "source_type": ""},
            },
            "section_3_tham_do_chuc_nang": {},
        },
        "abnormal_flags_summary": {"HIGH": [], "LOW": [], "POSITIVE_CULTURE": []},
    }


def test_merge_fills_values_and_keeps_all_fields():
    tpl = _template()
    sparse = {
        "document": {"record_number": "27713161"},
        "patient": {"full_name": "NGUYEN THI A", "year_of_birth": 1960},
        "groups": {
            "group_a_cbc": {
                "department": "Khoa Huyết học",
                "metadata": {"source_type": "pdf", "sample_collector": "Ngô Thu Hường"},
                "tests": [
                    {"stt": 2, "value": 12.95, "flag": "H", "device": "ADVIA2120i-A"},
                    {"stt": 3, "value": 89, "flag": "L"},
                ],
            },
            "group_b_coag": {
                "tests": [{"stt": 1, "sub_tests": [{"name": "PT-RP(s)", "value": 10.3}]}]
            },
            "group_c_vi_sinh": {"tests": [{"stt": 1, "value": "Enterococcus faecium"}]},
        },
        "imaging_and_functional": {"exam_xray": {"result": "Bình thường", "source_type": "image"}},
    }
    out = merge_sparse_into_template(tpl, sparse)

    # Values filled
    g = out["test_results"]["section_1_xet_nghiem"]["group_a_cbc"]
    assert g["department"] == "Khoa Huyết học"
    assert g["metadata"]["source_type"] == "pdf"
    assert g["metadata"]["sample_collector"] == "Ngô Thu Hường"
    assert g["tests"][0]["value"] == 12.95 and g["tests"][0]["flag"] == "H"
    assert g["tests"][0]["device"] == "ADVIA2120i-A"
    # Static fields preserved (not dropped)
    assert g["tests"][0]["name"] == "WBC"
    assert g["tests"][0]["reference_range"] == "4 - 10"
    # Sub-test matched by name
    sub = out["test_results"]["section_1_xet_nghiem"]["group_b_coag"]["tests"][0]["sub_tests"][0]
    assert sub["value"] == 10.3 and sub["name"] == "PT-RP(s)"
    # Imaging
    sec2 = out["test_results"]["section_2_chan_doan_hinh_anh"]
    assert sec2["exam_xray"]["result"] == "Bình thường"
    # Patient/document
    assert out["patient"]["full_name"] == "NGUYEN THI A"
    assert out["document"]["record_number"] == "27713161"


def test_merge_computes_abnormal_summary():
    tpl = _template()
    sparse = {
        "groups": {
            "group_a_cbc": {
                "tests": [
                    {"stt": 2, "value": 12.95, "flag": "H"},
                    {"stt": 3, "value": 89, "flag": "L"},
                ]
            },
            "group_c_vi_sinh": {"tests": [{"stt": 1, "value": "Enterococcus faecium"}]},
        }
    }
    out = merge_sparse_into_template(tpl, sparse)
    summ = out["abnormal_flags_summary"]
    assert any(e["test"] == "WBC" and e["value"] == 12.95 for e in summ["HIGH"])
    assert any(e["test"] == "HGB" for e in summ["LOW"])
    assert any(e["organism"] == "Enterococcus faecium" for e in summ["POSITIVE_CULTURE"])


def test_merge_ignores_unknown_keys_and_non_dict():
    tpl = _template()
    # Unknown group + non-dict sparse should not crash or corrupt structure.
    out = merge_sparse_into_template(tpl, {"groups": {"nope": {"tests": []}}})
    assert "group_a_cbc" in out["test_results"]["section_1_xet_nghiem"]
    out2 = merge_sparse_into_template(tpl, "not a dict")
    assert out2["test_results"]["section_1_xet_nghiem"]["group_a_cbc"]["tests"][0]["value"] is None


def test_merge_does_not_mutate_template():
    tpl = _template()
    snapshot = copy.deepcopy(tpl)
    sparse = {"groups": {"group_a_cbc": {"tests": [{"stt": 2, "value": 5}]}}}
    merge_sparse_into_template(tpl, sparse)
    assert tpl == snapshot  # original template untouched


def test_compute_abnormal_empty_when_no_flags():
    tpl = _template()
    summ = compute_abnormal_summary(tpl)
    assert summ == {"HIGH": [], "LOW": [], "POSITIVE_CULTURE": []}
