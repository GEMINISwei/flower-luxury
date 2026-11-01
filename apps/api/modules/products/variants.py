import uuid
from pathlib import Path
from threading import BoundedSemaphore, Lock

from pydantic import BaseModel

from .images import PREVIEW_SIZES, PhotoSize, PreparedPhoto, render_photo_variant
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


# 固定鎖不會在大量照片併發時被 LRU 淘汰, 讓同一張圖始終使用同一把鎖.
_GENERATION_LOCKS = tuple(Lock() for _ in range(128))
# 正式 API 只有 512 MB, 原圖匯入後的第一頁不能同時解碼整頁高解析度照片.
_REPAIR_SLOTS = BoundedSemaphore(2)


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
    target = display if size == "full" and not has_original else _variant_path(display, size)
    with _GENERATION_LOCKS[hash(display) % len(_GENERATION_LOCKS)]:
        if not target.is_file():
            source = original if has_original and original is not None else display
            with _REPAIR_SLOTS:
                rendered = render_photo_variant(source.read_bytes(), size)
                _write_atomic(target, rendered.content)
    return PhotoFile(path=target)
