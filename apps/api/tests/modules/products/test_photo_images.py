from io import BytesIO

import pytest
from PIL import Image

from modules.products.images import MAX_BATCH_BYTES, prepare_photo, validate_batch_size
from shared.http.errors import LangException


@pytest.mark.parametrize("format", ["JPEG", "PNG", "WEBP", "HEIF"])
def test_image_formats_preserve_original_and_decode_to_webp(format):
    buffer = BytesIO()
    Image.new("RGB", (16, 12), "red").save(buffer, format=format)
    data = buffer.getvalue()
    prepared = prepare_photo(data, None)
    assert prepared.original == data
    with Image.open(BytesIO(prepared.display)) as image:
        assert image.format == "WEBP" and image.size == (2560, 2560)
        assert not image.getexif()


@pytest.mark.parametrize("data", [b"", b"fake.jpg", b"<svg></svg>"])
def test_invalid_photo_content_rejected(data):
    with pytest.raises(LangException) as error:
        prepare_photo(data, "photo.jpg")
    assert error.value.status_code == 422


def test_photo_batch_limit():
    validate_batch_size([MAX_BATCH_BYTES])
    validate_batch_size([100] * 50)
    for sizes in [[], [0], [8 * 1024 * 1024, 8 * 1024 * 1024]]:
        with pytest.raises(LangException):
            validate_batch_size(sizes)
