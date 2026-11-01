from io import BytesIO
from typing import cast

import pytest
from PIL import Image

from modules.products.images import prepare_photo


def test_photo_variants_preserve_original_with_bounded_compressed_display():
    source = Image.new("RGB", (3000, 1500), (23, 100, 201))
    buffer = BytesIO()
    source.save(buffer, "PNG")
    prepared = prepare_photo(buffer.getvalue(), "large.png")
    assert prepared.original == buffer.getvalue()
    with Image.open(BytesIO(prepared.display)) as full:
        assert full.size == (2048, 1024)
        color = cast(tuple[int, ...], full.convert("RGBA").getpixel((1024, 512)))
        assert all(abs(actual - wanted) <= 6
                   for actual, wanted in zip(color, (23, 100, 201, 255), strict=True))
    for size in (128, 320, 640):
        with Image.open(BytesIO(prepared.previews[size])) as image:
            assert image.format == "WEBP" and image.size == (size, size)
            assert image.getchannel("A").getbbox() == (0, size // 4, size, size * 3 // 4)
            color = cast(tuple[int, ...], image.convert("RGBA").getpixel((size // 2, size // 2)))
            assert all(abs(actual - wanted) <= 6
                       for actual, wanted in zip(color, (23, 100, 201, 255), strict=True))
            assert not image.getexif()


def test_photo_variants_respect_orientation_and_transparency():
    source = Image.new("RGBA", (640, 320), (23, 100, 201, 128))
    exif = Image.Exif()
    exif[274] = 6
    buffer = BytesIO()
    source.save(buffer, "PNG", exif=exif)
    prepared = prepare_photo(buffer.getvalue(), "portrait.png")
    with Image.open(BytesIO(prepared.display)) as full:
        assert full.size == (320, 640) and not full.getexif()
        color = cast(tuple[int, ...], full.convert("RGBA").getpixel((160, 320)))
        assert color[3] == 128
        assert all(abs(actual - wanted) <= 6
                   for actual, wanted in zip(color[:3], (23, 100, 201), strict=True))
    for size in (128, 320, 640):
        with Image.open(BytesIO(prepared.previews[size])) as image:
            assert image.getchannel("A").getbbox() == (size // 4, 0, size * 3 // 4, size)
            color = cast(tuple[int, ...], image.convert("RGBA").getpixel((size // 2, size // 2)))
            assert color[3] == 128
            assert all(abs(actual - wanted) <= 6
                       for actual, wanted in zip(color[:3], (23, 100, 201), strict=True))
            assert cast(tuple[int, ...], image.convert("RGBA").getpixel((0, 0)))[3] == 0


@pytest.mark.parametrize("format", ["JPEG", "PNG", "WEBP", "HEIF"])
def test_preview_generation_supports_all_original_formats(format):
    buffer = BytesIO()
    Image.new("RGB", (32, 16), "red").save(buffer, format)
    prepared = prepare_photo(buffer.getvalue(), None)
    assert prepared.original == buffer.getvalue()
    assert set(prepared.previews) == {128, 320, 640}
    with Image.open(BytesIO(prepared.display)) as full:
        assert full.size == (32, 16)
