import json

import pytest

from extractor.core.template_parser import load_template_schema
from extractor.exceptions import TemplateError


def test_load_template_valid(tmp_path):
    p = tmp_path / "template.json"
    p.write_text(json.dumps({"document": {"title": "X"}}), encoding="utf-8")
    out = load_template_schema(p)
    assert json.loads(out) == {"document": {"title": "X"}}


def test_load_template_raises_on_broken_json(tmp_path):
    # Bệnh viện sửa template làm hỏng JSON -> báo lỗi rõ ràng (fallback)
    p = tmp_path / "template.json"
    p.write_text('{"document": {"title": "X"  "oops": 1}}', encoding="utf-8")
    with pytest.raises(TemplateError):
        load_template_schema(p)


def test_load_template_raises_on_non_object(tmp_path):
    p = tmp_path / "template.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(TemplateError):
        load_template_schema(p)
