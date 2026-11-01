from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from threading import Barrier, Lock

import pytest
from PIL import Image

from modules.products.variants import resolve_photo_variant


def original_file(tmp_path):
    source = tmp_path / "originals" / "photo.png"
    source.parent.mkdir()
    output = BytesIO()
    Image.new("RGB", (3000, 1500), (23, 100, 201)).save(output, "PNG")
    source.write_bytes(output.getvalue())
    return source


@pytest.mark.parametrize("size,dimensions", [
    ("128", (128, 128)), ("320", (320, 320)), ("640", (640, 640)),
    ("full", (2048, 1024)),
])
def test_repair_missing_variants_generates_only_requested_size(
    tmp_path, monkeypatch, size, dimensions,
):
    source = original_file(tmp_path)
    original = source.read_bytes()
    display = tmp_path / "display" / "photo.full.webp"
    save = Image.Image.save
    encoded = []

    def record(image, *args, **kwargs):
        encoded.append(image.size)
        return save(image, *args, **kwargs)

    monkeypatch.setattr(Image.Image, "save", record)
    result = resolve_photo_variant(display, source, size)
    assert encoded == [dimensions]
    assert list(display.parent.iterdir()) == [result.path]
    with Image.open(result.path) as image:
        assert image.size == dimensions and image.format == "WEBP"
    before = result.path.stat().st_mtime_ns
    assert resolve_photo_variant(display, source, size).path.stat().st_mtime_ns == before
    assert encoded == [dimensions] and source.read_bytes() == original


def test_repair_existing_preview_works_without_original_or_full_image(tmp_path):
    preview = tmp_path / "photo.128.webp"
    preview.write_bytes(b"existing")
    result = resolve_photo_variant(tmp_path / "photo.full.webp", tmp_path / "missing.png", "128")
    assert result.path == preview and preview.read_bytes() == b"existing"


def test_repair_without_any_source_reports_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        resolve_photo_variant(tmp_path / "photo.full.webp", None, "full")


def test_repair_write_failure_keeps_original_and_cleans_temporary_files(tmp_path, monkeypatch):
    source = original_file(tmp_path)
    original = source.read_bytes()
    display = tmp_path / "display" / "photo.full.webp"

    def fail_replace(path, target):
        raise OSError("disk unavailable")

    monkeypatch.setattr(Path, "replace", fail_replace)
    with pytest.raises(OSError, match="disk unavailable"):
        resolve_photo_variant(display, source, "128")
    assert source.read_bytes() == original
    assert not list(display.parent.iterdir())


def test_repair_concurrent_requests_encode_once(tmp_path, monkeypatch):
    source = original_file(tmp_path)
    display = tmp_path / "display" / "photo.full.webp"
    barrier = Barrier(4)
    mutex = Lock()
    save = Image.Image.save
    calls = []

    def record(image, *args, **kwargs):
        with mutex:
            calls.append(image.size)
        return save(image, *args, **kwargs)

    def read():
        barrier.wait(timeout=10)
        return resolve_photo_variant(display, source, "128").path

    monkeypatch.setattr(Image.Image, "save", record)
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda _: read(), range(4)))
    assert len(set(results)) == 1 and calls == [(128, 128)]
