"""Merge a *sparse* VLM response into the full template.

To cut latency, the VLM returns ONLY the data it found (values/flags + filled
metadata + admin fields), not the whole template scaffold. This module merges
that sparse payload back onto a deep copy of the template, so the final output
still contains every field (missing ones stay null/""). It also derives
``abnormal_flags_summary`` deterministically from the merged flags.

Sparse payload shape the model is asked to return::

    {
      "document": { <chỉ field có giá trị> },
      "patient":  { <chỉ field có giá trị> },
      "groups": {
        "<group_key>": {
          "department": "...", "time_collected": "...", "time_resulted": "...",
          "metadata": { <chỉ field có giá trị> },
          "tests": [
            { "stt": 8, "value": 5.67, "flag": "H", "device": "..." },
            { "stt": 1, "sub_tests": [ {"name": "PT-RP(s)", "value": 10.3} ] }
          ]
        }
      },
      "imaging_and_functional": { "<exam_key>": { "result": "...", ... } }
    }
"""

import copy
from typing import Any

from extractor.core import schema_keys as keys
from extractor.core.test_tree import is_filled, iter_leaf_tests

# Per-test fields the VLM may fill (everything else - name/reference_range/unit -
# is static and kept from the template).
LEAF_VALUE_FIELDS = ("value", "flag", "note", "process_code", "device")
GROUP_SCALAR_FIELDS = ("department", "time_collected", "time_resulted")
EXAM_FIELDS = ("name", "time_collected", "time_resulted", "result", "note", "source_type")


def _override(target: dict, src: Any, fields: tuple | None = None) -> None:
    """Copy filled (non-null, non-empty) values from ``src`` into ``target``."""
    if not isinstance(target, dict) or not isinstance(src, dict):
        return
    keys = fields if fields is not None else list(src.keys())
    for k in keys:
        if k in src and is_filled(src[k]):
            target[k] = src[k]


def _merge_subtests(t_subs: list, m_subs: Any) -> None:
    if not isinstance(m_subs, list):
        return
    by_name = {s.get("name"): s for s in t_subs if isinstance(s, dict) and s.get("name")}
    for ms in m_subs:
        if isinstance(ms, dict) and ms.get("name") in by_name:
            _override(by_name[ms["name"]], ms, LEAF_VALUE_FIELDS)


def _merge_tests(t_tests: list, m_tests: Any) -> None:
    if not isinstance(m_tests, list):
        return
    by_stt = {t["stt"]: t for t in t_tests if isinstance(t, dict) and t.get("stt") is not None}
    by_name = {t.get("name"): t for t in t_tests if isinstance(t, dict) and t.get("name")}
    for mt in m_tests:
        if not isinstance(mt, dict):
            continue
        tt = None
        if mt.get("stt") is not None:
            tt = by_stt.get(mt["stt"])
        if tt is None and mt.get("name"):
            tt = by_name.get(mt["name"])
        if tt is None:
            continue
        _override(tt, mt, LEAF_VALUE_FIELDS)
        if isinstance(tt.get("sub_tests"), list):
            _merge_subtests(tt["sub_tests"], mt.get("sub_tests"))


def _sparse_groups(sparse: dict) -> dict:
    groups = sparse.get(keys.SPARSE_GROUPS)
    if isinstance(groups, dict):
        return groups
    # Tolerate the model returning the full nested path instead of "groups".
    return (sparse.get(keys.TEST_RESULTS) or {}).get(keys.SECTION_LAB) or {}


def _sparse_exams(sparse: dict) -> dict:
    exams = sparse.get(keys.SPARSE_IMAGING_FUNCTIONAL)
    if isinstance(exams, dict):
        return exams
    merged: dict = {}
    tr = sparse.get(keys.TEST_RESULTS) or {}
    for sec in keys.EXAM_SECTIONS:
        if isinstance(tr.get(sec), dict):
            merged.update(tr[sec])
    return merged


def compute_abnormal_summary(result: dict) -> dict:
    """Derive HIGH/LOW/POSITIVE_CULTURE from the merged tests (deterministic)."""
    high: list[dict] = []
    low: list[dict] = []
    cultures: list[dict] = []
    s1 = (result.get(keys.TEST_RESULTS) or {}).get(keys.SECTION_LAB) or {}
    for group in s1.values():
        if not isinstance(group, dict):
            continue
        for leaf in iter_leaf_tests(group):
            flag = leaf.get("flag")
            entry = {
                "test": leaf.get("name", ""),
                "value": leaf.get("value"),
                "unit": leaf.get("unit"),
                "reference": leaf.get("reference_range"),
            }
            if flag == "H":
                high.append(entry)
            elif flag == "L":
                low.append(entry)
            name = (leaf.get("name") or "").lower()
            val = leaf.get("value")
            if "vi khu" in name and isinstance(val, str) and val.strip():
                cultures.append({"test": leaf.get("name"), "organism": val})
    return {"HIGH": high, "LOW": low, "POSITIVE_CULTURE": cultures}


def merge_sparse_into_template(template: dict, sparse: Any) -> dict:
    """Merge a sparse VLM payload onto a deep copy of the template.

    Returns the full record (all template fields present) with extracted values
    filled in and ``abnormal_flags_summary`` recomputed from the flags.
    """
    result = copy.deepcopy(template)
    if not isinstance(sparse, dict):
        result[keys.ABNORMAL_FLAGS_SUMMARY] = compute_abnormal_summary(result)
        return result

    _override(result.setdefault(keys.SPARSE_DOCUMENT, {}), sparse.get(keys.SPARSE_DOCUMENT))
    _override(result.setdefault(keys.SPARSE_PATIENT, {}), sparse.get(keys.SPARSE_PATIENT))

    tr = result.get(keys.TEST_RESULTS) or {}
    s1 = tr.get(keys.SECTION_LAB) or {}
    for gkey, gval in _sparse_groups(sparse).items():
        tgroup = s1.get(gkey)
        if not isinstance(tgroup, dict) or not isinstance(gval, dict):
            continue
        _override(tgroup, gval, GROUP_SCALAR_FIELDS)
        if isinstance(gval.get("metadata"), dict):
            _override(tgroup.setdefault("metadata", {}), gval["metadata"])
        _merge_tests(tgroup.get("tests") or [], gval.get("tests"))

    sec2 = tr.get(keys.SECTION_IMAGING) or {}
    sec3 = tr.get(keys.SECTION_FUNCTIONAL) or {}
    for exkey, exval in _sparse_exams(sparse).items():
        target = sec2.get(exkey) or sec3.get(exkey)
        if isinstance(target, dict) and isinstance(exval, dict):
            _override(target, exval, EXAM_FIELDS)

    result[keys.ABNORMAL_FLAGS_SUMMARY] = compute_abnormal_summary(result)
    return result
