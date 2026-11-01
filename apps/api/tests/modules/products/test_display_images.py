from io import BytesIO
from typing import cast

import pytest
from PIL import Image

from modules.products.images import prepare_photo


@pytest.mark.parametrize("size", [(16, 8), (8, 16), (5120, 2560), (12, 12)])
def test_display_photo_limits_long_edge_without_upscaling_or_cropping(size):
    buffer = BytesIO()
    Image.new("RGB", size, (23, 100, 201)).save(buffer, "PNG")
    result = prepare_photo(buffer.getvalue(), None).display
    with Image.open(BytesIO(result)) as image:
        ratio = min(1, 2048 / max(size))
        expected = tuple(max(1, round(edge * ratio)) for edge in size)
        assert image.size == expected and image.format == "WEBP"
        rgba = image.convert("RGBA")
        assert rgba.getchannel("A").getbbox() == (0, 0, *expected)
        color = cast(tuple[int, ...], rgba.getpixel((expected[0] // 2, expected[1] // 2)))
        assert all(abs(actual - wanted) <= 6
                   for actual, wanted in zip(color, (23, 100, 201, 255), strict=True))
        assert not image.getexif()


def test_display_photo_respects_exif_orientation():
    buffer = BytesIO()
    source = Image.new("RGB", (16, 8), "blue")
    exif = Image.Exif()
    exif[274] = 6
    source.save(buffer, "JPEG", exif=exif)
    with Image.open(BytesIO(prepare_photo(buffer.getvalue(), None).display)) as image:
        assert image.size == (8, 16)
        assert image.convert("RGBA").getchannel("A").getbbox() == (0, 0, 8, 16)
        assert not image.getexif()


def test_display_photo_preserves_existing_transparency():
    source = Image.new("RGBA", (640, 320), (0, 0, 0, 0))
    source.paste((23, 100, 201, 128), (160, 80, 480, 240))
    buffer = BytesIO()
    source.save(buffer, "PNG")
    with Image.open(BytesIO(prepare_photo(buffer.getvalue(), None).display)) as image:
        color = cast(tuple[int, ...], image.convert("RGBA").getpixel((320, 160)))
        assert color[3] == 128
        assert all(abs(actual - wanted) <= 6
                   for actual, wanted in zip(color[:3], (23, 100, 201), strict=True))
        assert cast(tuple[int, ...], image.getpixel((0, 0)))[3] == 0


def test_display_photo_compression_reduces_photographic_storage():
    source = Image.effect_noise((3000, 1500), 40).convert("RGB")
    original = BytesIO()
    source.save(original, "JPEG", quality=95)
    prepared = prepare_photo(original.getvalue(), "photo.jpg")
    baseline = BytesIO()
    with Image.open(BytesIO(original.getvalue())) as decoded:
        decoded.convert("RGBA").save(baseline, "WEBP", lossless=True, method=0)
    assert prepared.original == original.getvalue()
    assert len(prepared.display) < len(baseline.getvalue()) // 2
