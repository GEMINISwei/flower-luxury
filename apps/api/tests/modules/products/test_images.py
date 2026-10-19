from io import BytesIO

import pytest
from modules.products.images import decode_photo, validate_batch_size
from PIL import Image
from pillow_heif import register_heif_opener

from shared.http.errors import LangException

register_heif_opener()


def picture(format="PNG"):
    buffer = BytesIO()
    Image.new("RGB", (16, 12), "red").save(buffer, format=format)
    return buffer.getvalue()


@pytest.mark.parametrize("format", ["JPEG", "PNG", "WEBP", "HEIF"])
def test_image_formats_decode_to_webp(format):
    converted = decode_photo(picture(format))
    with Image.open(BytesIO(converted)) as image:
        assert image.format == "WEBP"
        assert image.size == (16, 12)
        assert not image.getexif()


@pytest.mark.parametrize("data", [b"", b"fake.jpg", b"<svg></svg>"])
def test_invalid_image_rejected(data):
    with pytest.raises(LangException) as error:
        decode_photo(data)
    assert error.value.status_code == 422


def test_photo_batch_limit():
    validate_batch_size([15 * 1024 * 1024])
    validate_batch_size([100] * 50)
    for sizes in [[], [0], [8 * 1024 * 1024, 8 * 1024 * 1024]]:
        with pytest.raises(LangException):
            validate_batch_size(sizes)
