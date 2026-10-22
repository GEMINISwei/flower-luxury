import warnings
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener

from shared.http.errors import BaseError, LangException, LangText

register_heif_opener()
MAX_BATCH_BYTES = 15 * 1024 * 1024


class PhotoError(BaseError):
    INVALID = LangText(zh="請選擇有效的 JPEG、PNG、WebP 或 HEIC 照片",
                      en="Choose a valid JPEG, PNG, WebP or HEIC photo")
    TOO_LARGE = LangText(zh="單次照片總容量不可超過 15MB，且檔案不可為空",
                        en="Photo batch must be at most 15MB and files must not be empty")


def validate_batch_size(sizes: list[int]) -> None:
    if not sizes or any(size <= 0 for size in sizes) or sum(sizes) > MAX_BATCH_BYTES:
        raise LangException(422, PhotoError.TOO_LARGE)


def decode_photo(data: bytes) -> bytes:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as source:
                if source.format not in {"JPEG", "PNG", "WEBP", "HEIF"}:
                    raise ValueError("unsupported format")
                source.thumbnail((2560, 2560))
                image = ImageOps.exif_transpose(source).convert("RGBA")
                output = BytesIO()
                image.save(output, "WEBP", quality=90)
                return output.getvalue()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as error:
        raise LangException(422, PhotoError.INVALID) from error
