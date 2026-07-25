"""Compute an extraction completeness report.

The pipeline merges every uploaded slip (PDF + image) into one record against a
comprehensive template. When the doctor forgets a file, the corresponding group
ends up entirely empty. This module derives -- deterministically, in code, not
from the VLM -- which groups / exams have NO extracted data, so the backend can
tell the user exactly what to upload more of. The report is attached to the
output under ``extraction_meta``.
"""

from extractor.core import schema_keys as keys
from extractor.core.test_tree import is_filled, iter_leaf_tests


def _normalize_unrecognized(items: object) -> list[dict]:
    """Normalize the VLM's unrecognized-source list to ``[{file, reason}]``.

    Accepts either plain filenames (older shape) or objects with file/reason.
    """
    out: list[dict] = []
    if not isinstance(items, list):
        return out
    for it in items:
        if isinstance(it, dict):
            out.append({"file": it.get("file", ""), "reason": it.get("reason", "")})
        elif isinstance(it, str):
            out.append({"file": it, "reason": ""})
    return out


def build_extraction_meta(
    result: dict,
    manifest: list[dict] | None = None,
    unrecognized_sources: object = None,
    low_fill_threshold: float = 0.5,
) -> dict:
    """Build the ``extraction_meta`` block summarizing extraction completeness.

    Args:
        result: The extracted record (already conforming to the template).
        manifest: Per-file manifest (which files/pages were processed).
        unrecognized_sources: Files the VLM flagged as not matching the template
            (filenames or ``{file, reason}`` objects); normalized to objects.
        low_fill_threshold: Warn when ``0 < fill_rate < this`` (0..1).

    Returns:
        A dict with processed files, unrecognized sources, human-readable
        ``warnings`` for the backend, and a completeness report. ``empty_groups``
        is the actionable signal: a lab group with zero filled values most likely
        means the doctor has not uploaded that slip yet.
    """
    sections = result.get(keys.TEST_RESULTS) or {}
    s1 = sections.get(keys.SECTION_LAB) or {}

    total = filled = 0
    empty_groups: list[str] = []
    partial_groups: list[str] = []
    for gname, group in s1.items():
        if not isinstance(group, dict):
            continue
        leaves = list(iter_leaf_tests(group))
        if not leaves:
            continue
        g_filled = sum(1 for t in leaves if is_filled(t.get("value")))
        total += len(leaves)
        filled += g_filled
        if g_filled == 0:
            empty_groups.append(gname)
        elif g_filled < len(leaves):
            partial_groups.append(gname)

    def _empty_exams(section_key: str) -> list[str]:
        sec = sections.get(section_key) or {}
        return [
            name
            for name, exam in sec.items()
            if isinstance(exam, dict) and not is_filled(exam.get("result"))
        ]

    empty_imaging = _empty_exams(keys.SECTION_IMAGING)
    empty_functional = _empty_exams(keys.SECTION_FUNCTIONAL)

    def _exams_have_data(section_key: str) -> bool:
        sec = sections.get(section_key) or {}
        return any(isinstance(ex, dict) and is_filled(ex.get("result")) for ex in sec.values())

    patient_named = is_filled((result.get("patient") or {}).get("full_name"))
    # Distinguishes a real (but partial) upload from an irrelevant / unreadable
    # one: if NOTHING at all was extracted, the user likely uploaded the wrong
    # files. The backend pairs this with `unrecognized_sources` to tell the user.
    has_usable_data = bool(
        filled
        or patient_named
        or _exams_have_data(keys.SECTION_IMAGING)
        or _exams_have_data(keys.SECTION_FUNCTIONAL)
    )

    fill_rate = round(filled / total, 3) if total else 0.0
    low_fill_rate = bool(has_usable_data and total and fill_rate < low_fill_threshold)
    unrecognized = _normalize_unrecognized(unrecognized_sources)

    # Ready-to-show messages for the backend / user.
    warnings: list[str] = []
    if not has_usable_data:
        warnings.append(
            "Khong trich xuat duoc du lieu nao - kiem tra lai file (co the khong "
            "phai phieu xet nghiem hoac khong doc duoc)."
        )
    if low_fill_rate:
        warnings.append(
            f"Ti le dien thap ({round(fill_rate * 100)}%) - co the thieu phieu hoac anh mo/kho doc."
        )
    if empty_groups:
        warnings.append(
            f"{len(empty_groups)} nhom xet nghiem chua co du lieu - co the thieu phieu."
        )
    if unrecognized:
        names = ", ".join(u["file"] or "?" for u in unrecognized)
        warnings.append(f"File khong lien quan/khong nhan dien duoc: {names}.")

    return {
        "processed_files": manifest or [],
        "unrecognized_sources": unrecognized,
        "warnings": warnings,
        "completeness": {
            "total_test_fields": total,
            "filled_test_fields": filled,
            "fill_rate": fill_rate,
            "has_usable_data": has_usable_data,
            "low_fill_rate": low_fill_rate,
            "empty_groups": empty_groups,
            "partial_groups": partial_groups,
            "empty_imaging": empty_imaging,
            "empty_functional": empty_functional,
            # Actionable flag for the backend: something has no data at all.
            "has_missing_data": bool(empty_groups or empty_imaging or empty_functional),
        },
    }
