import warnings
from io import BytesIO
from typing import Literal

from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener
from pydantic import BaseModel, Field

from shared.http.errors import LangException

from .errors import PhotoError

register_heif_opener()
MAX_BATCH_BYTES = 15 * 1024 * 1024
PREVIEW_SIZES = (128, 320, 640)
DISPLAY_MAX_EDGE = 2048
type PhotoSize = Literal["128", "320", "640", "full"]
FORMATS = {"JPEG": ("jpg", "image/jpeg"), "PNG": ("png", "image/png"),
           "WEBP": ("webp", "image/webp"), "HEIF": ("heic", "image/heic")}


class PreparedPhoto(BaseModel):
    original: bytes
    display: bytes
    filename: str
    extension: str
    media_type: str
    previews: dict[int, bytes] = Field(default_factory=dict)


class RenderedPhoto(BaseModel):
    content: bytes


def validate_batch_size(sizes: list[int], *, status_code: int = 422) -> None:
    if not sizes or any(size <= 0 for size in sizes) or sum(sizes) > MAX_BATCH_BYTES:
        raise LangException(status_code, PhotoError.TOO_LARGE)


def _webp(image: Image.Image) -> bytes:
    output = BytesIO()
    image.save(output, "WEBP", quality=85, exact=True, method=4)
    return output.getvalue()


def _preview(image: Image.Image, size: int) -> bytes:
    ratio = min(size / image.width, size / image.height)
    dimensions = (max(1, round(image.width * ratio)), max(1, round(image.height * ratio)))
    # 分開縮放色彩與 alpha, 避免預乘 alpha 的整數往返改變半透明區域的原色.
    fitted = Image.merge("RGBA", tuple(channel.resize(dimensions, Image.Resampling.LANCZOS)
                                      for channel in image.split()))
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    position = ((size - fitted.width) // 2, (size - fitted.height) // 2)
    canvas.paste(fitted, position)
    return _webp(canvas)


def _decode(data: bytes) -> tuple[Image.Image, str, str]:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as source:
                if source.format not in FORMATS:
                    raise ValueError("unsupported format")
                extension, media_type = FORMATS[str(source.format)]
                image = ImageOps.exif_transpose(source).convert("RGBA")
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as error:
        raise LangException(422, PhotoError.INVALID) from error
    return image, extension, media_type


def _render(image: Image.Image, size: PhotoSize) -> bytes:
    if size != "full":
        return _preview(image, int(size))
    ratio = min(1, DISPLAY_MAX_EDGE / max(image.size))
    if ratio == 1:
        return _webp(image)
    dimensions = tuple(max(1, round(edge * ratio)) for edge in image.size)
    fitted = Image.merge("RGBA", tuple(channel.resize(dimensions, Image.Resampling.LANCZOS)
                                      for channel in image.split()))
    return _webp(fitted)


def render_photo_variant(data: bytes, size: PhotoSize) -> RenderedPhoto:
    image, _, _ = _decode(data)
    with image:
        return RenderedPhoto(content=_render(image, size))


def prepare_photo(data: bytes, filename: str | None) -> PreparedPhoto:
    image, extension, media_type = _decode(data)
    with image:
        display = _render(image, "full")
        previews = {size: _preview(image, size) for size in PREVIEW_SIZES}
    name = (filename or f"photo.{extension}").replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(char for char in name if ord(char) >= 32 and ord(char) != 127)
    return PreparedPhoto(original=data, display=display, previews=previews, extension=extension,
                         media_type=media_type, filename=name[:255] or f"photo.{extension}")
