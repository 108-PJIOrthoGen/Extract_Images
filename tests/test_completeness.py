from extractor.core.completeness import build_extraction_meta


def _result():
    return {
        "test_results": {
            "section_1_xet_nghiem": {
                "group_filled": {
                    "tests": [
                        {"name": "WBC", "value": 6.2},
                        {"name": "RBC", "value": 4.1},
                    ]
                },
                "group_partial": {
                    "tests": [
                        {"name": "A", "value": 1},
                        {"name": "B", "value": None},
                    ]
                },
                "group_empty": {
                    "tests": [
                        {"name": "X", "value": None},
                        {"name": "Y", "value": ""},
                    ]
                },
                "group_subtests": {
                    "tests": [
                        {
                            "category": "PT",
                            "sub_tests": [
                                {"name": "PT-s", "value": 10.3},
                                {"name": "PT-%", "value": None},
                            ],
                        }
                    ]
                },
            },
            "section_2_chan_doan_hinh_anh": {
                "xray": {"result": "Bình thường"},
                "xray_empty": {"result": ""},
            },
            "section_3_tham_do_chuc_nang": {
                "ecg": {"result": None},
            },
        }
    }


def test_completeness_flags_empty_and_partial_groups():
    meta = build_extraction_meta(_result(), manifest=[{"file": "a.pdf"}])
    c = meta["completeness"]

    assert meta["processed_files"] == [{"file": "a.pdf"}]
    assert c["empty_groups"] == ["group_empty"]
    assert "group_partial" in c["partial_groups"]
    assert "group_subtests" in c["partial_groups"]
    # 2 (filled) + 1 (partial) + 0 (empty) + 1 (subtests) = 4 filled of 8 leaves
    assert c["total_test_fields"] == 8
    assert c["filled_test_fields"] == 4
    assert c["fill_rate"] == 0.5
    assert c["empty_imaging"] == ["xray_empty"]
    assert c["empty_functional"] == ["ecg"]
    assert c["has_missing_data"] is True
    assert c["has_usable_data"] is True
    # fill_rate 0.5 is NOT below the default 0.5 threshold.
    assert c["low_fill_rate"] is False
    assert any("nhom xet nghiem" in w for w in meta["warnings"])


def test_low_fill_rate_warning():
    meta = build_extraction_meta(_result(), low_fill_threshold=0.6)
    c = meta["completeness"]
    assert c["fill_rate"] == 0.5
    assert c["low_fill_rate"] is True
    assert any("Ti le dien thap" in w for w in meta["warnings"])


def test_unrecognized_sources_normalized_with_reason():
    result = {
        "patient": {"full_name": "A"},
        "test_results": {"section_1_xet_nghiem": {}},
    }
    meta = build_extraction_meta(
        result,
        unrecognized_sources=[
            {"file": "hoa_don.pdf", "reason": "Hoa don tien dien"},
            "anh_meo.jpg",  # legacy plain string -> normalized
        ],
    )
    assert meta["unrecognized_sources"] == [
        {"file": "hoa_don.pdf", "reason": "Hoa don tien dien"},
        {"file": "anh_meo.jpg", "reason": ""},
    ]
    assert any("khong nhan dien" in w for w in meta["warnings"])


def test_completeness_flags_irrelevant_upload_as_unusable():
    # Nothing extracted at all (e.g. user uploaded an unrelated file).
    result = {
        "patient": {"full_name": ""},
        "test_results": {
            "section_1_xet_nghiem": {"g": {"tests": [{"name": "WBC", "value": None}]}},
            "section_2_chan_doan_hinh_anh": {"x": {"result": ""}},
            "section_3_tham_do_chuc_nang": {},
        },
    }
    c = build_extraction_meta(result)["completeness"]
    assert c["has_usable_data"] is False
    assert c["fill_rate"] == 0.0


def test_completeness_no_missing_when_all_filled():
    result = {
        "test_results": {
            "section_1_xet_nghiem": {"g": {"tests": [{"name": "WBC", "value": 6.2}]}},
            "section_2_chan_doan_hinh_anh": {},
            "section_3_tham_do_chuc_nang": {},
        }
    }
    c = build_extraction_meta(result)["completeness"]
    assert c["empty_groups"] == []
    assert c["has_missing_data"] is False
    assert c["has_usable_data"] is True
    assert c["fill_rate"] == 1.0
