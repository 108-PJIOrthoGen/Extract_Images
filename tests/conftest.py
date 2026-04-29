import json

import pytest


@pytest.fixture
def sample_template_path(tmp_path):
    template = {"document": {"title": "Test", "patient": {"name": ""}}}
    p = tmp_path / "template.json"
    p.write_text(json.dumps(template))
    return p


@pytest.fixture
def sample_image_dir(tmp_path):
    img_dir = tmp_path / "images"
    img_dir.mkdir()
    import base64

    png_data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )
    (img_dir / "page_1.png").write_bytes(png_data)
    return img_dir
