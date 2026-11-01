import time
from pathlib import Path

HEARTBEAT_PATH = Path("/tmp/line-collector-heartbeat")  # noqa: S108


def is_healthy(path: Path = HEARTBEAT_PATH, *, now: float | None = None) -> bool:
    try:
        age = (time.time() if now is None else now) - path.stat().st_mtime
    except OSError:
        return False
    return 0 <= age <= 30


if __name__ == "__main__":
    raise SystemExit(0 if is_healthy() else 1)
