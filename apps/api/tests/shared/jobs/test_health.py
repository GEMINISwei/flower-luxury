import os

from shared.jobs.health import is_healthy


def test_healthcheck_rejects_missing_stale_and_future_heartbeat(tmp_path):
    path = tmp_path / "heartbeat"
    assert not is_healthy(path, now=100)
    path.touch()
    os.utime(path, (95, 95))
    assert is_healthy(path, now=100)
    assert not is_healthy(path, now=200)
    assert not is_healthy(path, now=90)
