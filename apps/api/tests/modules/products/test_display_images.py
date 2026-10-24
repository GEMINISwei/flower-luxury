from io import BytesIO
from typing import cast

import pytest
from PIL import Image

from modules.products.images import decode_photo


@pytest.mark.parametrize("size", [(16, 8), (8, 16), (5120, 2560), (12, 12)])
def test_display_photo_fits_canvas_without_cropping_or_background_removal(size):
    buffer = BytesIO()
    Image.new("RGB", size, (23, 100, 201)).save(buffer, "PNG")
    result = decode_photo(buffer.getvalue(), canvas_size=(2560, 2560))
    with Image.open(BytesIO(result)) as image:
        assert image.size == (2560, 2560) and image.format == "WEBP"
        rgba = image.convert("RGBA")
        bounds = rgba.getchannel("A").getbbox()
        expected = ((0, 640, 2560, 1920) if size[0] > size[1] else
                    (640, 0, 1920, 2560) if size[0] < size[1] else (0, 0, 2560, 2560))
        assert bounds == expected
        assert rgba.getpixel((1280, 1280)) == (23, 100, 201, 255)
        assert rgba.getpixel((expected[0], expected[1])) == (23, 100, 201, 255)
        assert not image.getexif()


def test_display_photo_respects_exif_orientation():
    buffer = BytesIO()
    source = Image.new("RGB", (16, 8), "blue")
    exif = Image.Exif()
    exif[274] = 6
    source.save(buffer, "JPEG", exif=exif)
    with Image.open(BytesIO(decode_photo(buffer.getvalue(), canvas_size=(2560, 2560)))) as image:
        assert image.getchannel("A").getbbox() == (640, 0, 1920, 2560)
        assert not image.getexif()


def test_display_photo_preserves_existing_transparency():
    source = Image.new("RGBA", (2560, 2560), (0, 0, 0, 0))
    source.putpixel((1280, 1280), (23, 100, 201, 128))
    buffer = BytesIO()
    source.save(buffer, "PNG")
    with Image.open(BytesIO(decode_photo(buffer.getvalue(), canvas_size=(2560, 2560)))) as image:
        assert image.getpixel((1280, 1280)) == (23, 100, 201, 128)
        assert cast(tuple[int, ...], image.getpixel((0, 0)))[3] == 0
