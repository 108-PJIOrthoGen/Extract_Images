import pytest
from PIL import Image
from pillow_heif import from_pillow

from extractor.loaders.constants import (
    IMAGE_EXTENSIONS,
    MIME_MAP,
    PDF_EXTENSIONS,
    SUPPORTED_EXTENSIONS,
)
from extractor.loaders.image_loader import (
    get_base64_image,
    load_directory_with_manifest,
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

    def test_get_base64_image_decodes_heic_to_jpeg_data_url(self, tmp_path):
        image = Image.new("RGB", (2, 2), color=(220, 30, 30))
        heif = from_pillow(image)
        image_path = tmp_path / "camera.heic"
        heif.save(image_path, quality=90)

        result = get_base64_image(image_path)

        assert result.startswith("data:image/jpeg;base64,")

    def test_get_base64_image_defaults_to_jpeg_for_unknown_extension(self, tmp_path):
        img_path = tmp_path / "test.xyz"
        img_path.write_bytes(b"fake data")
        result = get_base64_image(img_path)
        assert result.startswith("data:image/jpeg;base64,")

    def test_load_directory_returns_parts_and_manifest(self, sample_image_dir):
        parts, manifest = load_directory_with_manifest(sample_image_dir)
        assert isinstance(parts, list)
        assert len(parts) == 1
        assert len(manifest) == 1

    def test_load_directory_returns_empty_for_missing_dir(self, tmp_path):
        parts, manifest = load_directory_with_manifest(tmp_path / "nope")
        assert parts == []
        assert manifest == []

    def test_load_directory_ignores_non_image_files(self, tmp_path):
        img_dir = tmp_path / "images"
        img_dir.mkdir()
        (img_dir / "test.txt").write_text("not an image")
        (img_dir / "test.py").write_text("print('hello')")

        parts, manifest = load_directory_with_manifest(img_dir)
        assert parts == []
        assert manifest == []

    def test_mime_map_contains_expected_extensions(self):
        expected = {
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
            ".bmp",
            ".tiff",
            ".tif",
            ".heic",
            ".heif",
        }
        assert MIME_MAP.keys() == expected

    def test_image_extensions_match_mime_map(self):
        assert MIME_MAP.keys() == IMAGE_EXTENSIONS

    def test_supported_extensions_include_images_and_pdf(self):
        assert SUPPORTED_EXTENSIONS == IMAGE_EXTENSIONS | PDF_EXTENSIONS
        assert ".pdf" in PDF_EXTENSIONS

    def test_blank_pdf_pages_become_image_parts(self, tmp_path):
        import fitz

        doc_dir = tmp_path / "docs"
        doc_dir.mkdir()
        # A 2-page blank PDF (no text layer) -> 2 rendered image parts.
        pdf = fitz.open()
        pdf.new_page()
        pdf.new_page()
        pdf.save(doc_dir / "scanned.pdf")
        pdf.close()

        parts, _ = load_directory_with_manifest(doc_dir)
        assert len(parts) == 2
        assert all(p["type"] == "image_url" for p in parts)
        assert all(p["image_url"]["url"].startswith("data:image/png;base64,") for p in parts)

    def test_text_pdf_becomes_text_part(self, tmp_path):
        import fitz

        doc_dir = tmp_path / "docs"
        doc_dir.mkdir()
        pdf = fitz.open()
        page = pdf.new_page()
        page.insert_text(
            (72, 100),
            "\n".join(["PHIEU XET NGHIEM HUYET HOC", "WBC 6.2 G/L", "HGB 130 g/L"] * 4),
            fontsize=11,
        )
        pdf.save(doc_dir / "born_digital.pdf")
        pdf.close()

        parts, _ = load_directory_with_manifest(doc_dir)
        assert len(parts) == 1
        assert parts[0]["type"] == "text"
        assert "WBC" in parts[0]["text"]
        assert "born_digital.pdf" in parts[0]["text"]

    def test_manifest_maps_mixed_files_to_pages(self, tmp_path):
        import base64 as _b64

        import fitz

        doc_dir = tmp_path / "case"
        doc_dir.mkdir()

        # One image (1 page) + one 2-page scanned (blank) PDF.
        png = _b64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
            "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        (doc_dir / "a_image.png").write_bytes(png)
        pdf = fitz.open()
        pdf.new_page()
        pdf.new_page()
        pdf.save(doc_dir / "b_report.pdf")
        pdf.close()

        pages, manifest = load_directory_with_manifest(doc_dir)
        assert len(pages) == 3
        assert len(manifest) == 2
        # Sorted by name: a_image.png (page 1), b_report.pdf (pages 2-3).
        assert manifest[0] == {
            "file": "a_image.png",
            "type": "image",
            "mode": "image",
            "pages": 1,
            "page_start": 1,
            "page_end": 1,
        }
        assert manifest[1] == {
            "file": "b_report.pdf",
            "type": "pdf",
            "mode": "image",
            "pages": 2,
            "page_start": 2,
            "page_end": 3,
        }
