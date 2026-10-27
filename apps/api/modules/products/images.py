import warnings
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener
from pydantic import BaseModel

from shared.http.errors import LangException

from .errors import PhotoError

register_heif_opener()
MAX_BATCH_BYTES = 15 * 1024 * 1024
DISPLAY_SIZE = (2560, 2560)
FORMATS = {"JPEG": ("jpg", "image/jpeg"), "PNG": ("png", "image/png"),
           "WEBP": ("webp", "image/webp"), "HEIF": ("heic", "image/heic")}


class PreparedPhoto(BaseModel):
    original: bytes
    display: bytes
    filename: str
    extension: str
    media_type: str


def validate_batch_size(sizes: list[int]) -> None:
    if not sizes or any(size <= 0 for size in sizes) or sum(sizes) > MAX_BATCH_BYTES:
        raise LangException(422, PhotoError.TOO_LARGE)


def _decode_photo(data: bytes, *, canvas_size: tuple[int, int] | None = None) -> bytes:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as source:
                if source.format not in FORMATS:
                    raise ValueError("unsupported format")
                image = ImageOps.exif_transpose(source).convert("RGBA")
                if canvas_size:
                    fitted = ImageOps.contain(image, canvas_size, Image.Resampling.LANCZOS)
                    image = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
                    position = ((canvas_size[0] - fitted.width) // 2,
                                (canvas_size[1] - fitted.height) // 2)
                    image.paste(fitted, position)
                else:
                    image.thumbnail(DISPLAY_SIZE)
                output = BytesIO()
                image.save(output, "WEBP", lossless=True, exact=True)
                return output.getvalue()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as error:
        raise LangException(422, PhotoError.INVALID) from error


def prepare_photo(data: bytes, filename: str | None) -> PreparedPhoto:
    display = _decode_photo(data, canvas_size=DISPLAY_SIZE)
    with Image.open(BytesIO(data)) as source:
        extension, media_type = FORMATS[str(source.format)]
    name = (filename or f"photo.{extension}").replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(char for char in name if ord(char) >= 32 and ord(char) != 127)
    return PreparedPhoto(original=data, display=display, extension=extension,
                         media_type=media_type, filename=name[:255] or f"photo.{extension}")
