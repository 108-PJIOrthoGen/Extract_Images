from pathlib import Path

import pytest

from extractor.loaders.image_loader import (
    MIME_MAP,
    SUPPORTED_EXTENSIONS,
    get_base64_image,
    load_images_from_directory,
)


class TestImageLoader:
    def test_get_base64_image_returns_data_url(self, sample_image_dir):
        image_path = sample_image_dir / "page_1.png"
        result = get_base64_image(image_path)
        assert result.startswith("data:image/png;base64,")
        assert len(result) > len("data:image/png;base64,")

    def test_get_base64_image_accepts_string_path(self, sample_image_dir):
        result = get_base64_image(str(sample_image_dir / "page_1.png"))
        assert result.startswith("data:image/png;base64,")

    def test_get_base64_image_raises_on_missing_file(self):
        with pytest.raises(FileNotFoundError):
            get_base64_image("/nonexistent/path.png")

    def test_get_base64_image_handles_jpeg_extension(self, tmp_path):
        img_path = tmp_path / "test.jpg"
        img_path.write_bytes(b"fake jpeg data")
        result = get_base64_image(img_path)
        assert result.startswith("data:image/jpeg;base64,")

    def test_get_base64_image_handles_webp_extension(self, tmp_path):
        img_path = tmp_path / "test.webp"
        img_path.write_bytes(b"fake webp data")
        result = get_base64_image(img_path)
        assert result.startswith("data:image/webp;base64,")

    def test_get_base64_image_defaults_to_jpeg_for_unknown_extension(self, tmp_path):
        img_path = tmp_path / "test.xyz"
        img_path.write_bytes(b"fake data")
        result = get_base64_image(img_path)
        assert result.startswith("data:image/jpeg;base64,")

    def test_load_images_from_directory_returns_list(self, sample_image_dir):
        result = load_images_from_directory(sample_image_dir)
        assert isinstance(result, list)
        assert len(result) == 1

    def test_load_images_from_directory_returns_empty_for_missing_dir(self):
        result = load_images_from_directory(Path("/nonexistent/dir"))
        assert result == []

    def test_load_images_from_directory_ignores_non_image_files(self, tmp_path):
        img_dir = tmp_path / "images"
        img_dir.mkdir()
        (img_dir / "test.txt").write_text("not an image")
        (img_dir / "test.py").write_text("print('hello')")

        result = load_images_from_directory(img_dir)
        assert result == []

    def test_mime_map_contains_expected_extensions(self):
        expected = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}
        assert MIME_MAP.keys() == expected

    def test_supported_extensions_matches_mime_map(self):
        assert MIME_MAP.keys() == SUPPORTED_EXTENSIONS
