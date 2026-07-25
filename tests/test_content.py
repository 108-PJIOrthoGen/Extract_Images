from extractor.loaders.content import image_part, part_kind, text_part


def test_text_part_shape():
    part = text_part("hello")
    assert part == {"type": "text", "text": "hello"}


def test_image_part_shape():
    url = "data:image/png;base64,AAAA"
    part = image_part(url)
    assert part == {"type": "image_url", "image_url": {"url": url}}


def test_part_kind_text():
    assert part_kind(text_part("x")) == "text"


def test_part_kind_image():
    assert part_kind(image_part("data:image/png;base64,AAAA")) == "image"


def test_part_kind_defaults_to_image_for_unknown():
    # Anything that is not an explicit text part is treated as an image part.
    assert part_kind({"type": "image_url"}) == "image"
    assert part_kind({}) == "image"
