"""Shared helpers for walking the test/sub-test tree of a result record.

Both :mod:`extractor.core.completeness` and :mod:`extractor.core.sparse_merge`
need to iterate the leaf tests of a group and decide whether a field is filled.
Keeping these helpers here avoids cross-importing private functions between
those modules.
"""

from collections.abc import Iterator
from typing import Any


def iter_leaf_tests(group: dict) -> Iterator[dict]:
    """Yield each leaf test of a group (a test, or each of its ``sub_tests``)."""
    for test in group.get("tests") or []:
        if not isinstance(test, dict):
            continue
        subs = test.get("sub_tests")
        if isinstance(subs, list) and subs:
            yield from (s for s in subs if isinstance(s, dict))
        else:
            yield test


def is_filled(value: Any) -> bool:
    """A field counts as filled when it is not ``None`` and not an empty string."""
    return value is not None and value != ""
