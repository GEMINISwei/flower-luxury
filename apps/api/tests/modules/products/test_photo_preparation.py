from io import BytesIO

import pytest
from fastapi import UploadFile
from PIL import Image

from modules.products.images import MAX_BATCH_BYTES, prepare_photo
from modules.products.photos import read_batch
from shared.http.errors import LangException


def picture(format="PNG"):
    buffer = BytesIO()
    Image.new("RGB", (16, 8), "red").save(buffer, format)
    return buffer.getvalue()


def test_original_format_uses_content_instead_of_filename():
    data = picture("JPEG")
    photo = prepare_photo(data, "misleading.png")
    assert photo.original == data
    assert photo.extension == "jpg" and photo.media_type == "image/jpeg"
    assert photo.filename == "misleading.png"
    with Image.open(BytesIO(photo.display)) as image:
        assert image.format == "WEBP" and image.size == (16, 8)


@pytest.mark.parametrize("name,expected", [
    ("C:\\fakepath\\photo.png\r\n", "photo.png"), ("../../photo.png", "photo.png"),
    (None, "photo.png"), ("\r\n", "photo.png"),
])
def test_original_download_filename_removes_paths_and_control_characters(name, expected):
    assert prepare_photo(picture(), name).filename == expected


@pytest.mark.asyncio
async def test_read_batch_checks_total_size_before_converting():
    original = picture()
    first = UploadFile(filename="first.png", file=BytesIO(original))
    second = UploadFile(filename="large.png", file=BytesIO(b"x" * (MAX_BATCH_BYTES + 20)))
    with pytest.raises(LangException) as error:
        await read_batch([first, second])
    assert error.value.status_code == 422
    assert second.file.tell() == MAX_BATCH_BYTES - len(original) + 1


@pytest.mark.asyncio
async def test_read_batch_rejects_invalid_content_even_with_supported_filename():
    with pytest.raises(LangException) as error:
        await read_batch([UploadFile(filename="fake.jpg", file=BytesIO(b"not an image"))])
    assert error.value.status_code == 422


@pytest.mark.asyncio
async def test_read_batch_preserves_original_and_filename():
    original = picture()
    result = await read_batch([UploadFile(filename="original.png", file=BytesIO(original))])
    assert len(result.photos) == 1 and result.photos[0].original == original
    assert result.photos[0].filename == "original.png"


@pytest.mark.asyncio
@pytest.mark.parametrize("files", [[], [UploadFile(filename="empty.png", file=BytesIO())]])
async def test_read_batch_rejects_empty_uploads(files):
    with pytest.raises(LangException) as error:
        await read_batch(files)
    assert error.value.status_code == 422
