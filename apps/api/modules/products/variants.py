import uuid
from functools import lru_cache
from pathlib import Path
from threading import Lock

from pydantic import BaseModel

from .images import PREVIEW_SIZES, PhotoSize, PreparedPhoto, prepare_photo
from .schema import PhotoFile


class PhotoVariantFiles(BaseModel):
    paths: list[Path]


def _variant_path(display: Path, size: str) -> Path:
    stem = display.stem.removesuffix(".full")
    return display.with_name(f"{stem}.{size}.webp")


def photo_variant_files(display: Path) -> PhotoVariantFiles:
    # 舊檔名與完整解析度檔名都要清理, 包含尚未補產的衍生檔.
    paths = [display, _variant_path(display, "full")]
    paths.extend(_variant_path(display, str(size)) for size in PREVIEW_SIZES)
    return PhotoVariantFiles(paths=list(dict.fromkeys(paths)))


def write_photo_variants(display: Path, prepared: PreparedPhoto, created: list[Path]) -> None:
    content = [(display, prepared.display)]
    content.extend((_variant_path(display, str(size)), data)
                   for size, data in prepared.previews.items())
    for path, data in content:
        created.append(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


@lru_cache(maxsize=128)
def _generation_lock(_display: Path) -> Lock:
    # 同一照片可能同時出現在主圖與訊息區, 避免首次讀取重複轉檔.
    return Lock()


def _write_atomic(path: Path, data: bytes) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_bytes(data)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def resolve_photo_variant(display: Path, original: Path | None, size: PhotoSize) -> PhotoFile:
    has_original = original is not None and original.is_file()
    if size == "full" and not has_original:
        return PhotoFile(path=display)
    target = _variant_path(display, size)
    with _generation_lock(display):
        if not target.is_file():
            source = original if has_original and original is not None else display
            prepared = prepare_photo(source.read_bytes(), None)
            files = [(_variant_path(display, "full"), prepared.display)]
            files.extend((_variant_path(display, str(edge)), data)
                         for edge, data in prepared.previews.items())
            for path, data in files:
                if not path.is_file():
                    _write_atomic(path, data)
    return PhotoFile(path=target)
