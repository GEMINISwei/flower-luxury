from io import BytesIO
from typing import cast

import pytest
from PIL import Image

from modules.products.images import prepare_photo


@pytest.mark.parametrize("size", [(16, 8), (8, 16), (5120, 2560), (12, 12)])
def test_display_photo_preserves_original_dimensions_without_cropping(size):
    buffer = BytesIO()
    Image.new("RGB", size, (23, 100, 201)).save(buffer, "PNG")
    result = prepare_photo(buffer.getvalue(), None).display
    with Image.open(BytesIO(result)) as image:
        assert image.size == size and image.format == "WEBP"
        rgba = image.convert("RGBA")
        assert rgba.getchannel("A").getbbox() == (0, 0, *size)
        assert rgba.getpixel((size[0] // 2, size[1] // 2)) == (23, 100, 201, 255)
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
    source = Image.new("RGBA", (2560, 2560), (0, 0, 0, 0))
    source.putpixel((1280, 1280), (23, 100, 201, 128))
    buffer = BytesIO()
    source.save(buffer, "PNG")
    with Image.open(BytesIO(prepare_photo(buffer.getvalue(), None).display)) as image:
        assert image.getpixel((1280, 1280)) == (23, 100, 201, 128)
        assert cast(tuple[int, ...], image.getpixel((0, 0)))[3] == 0
