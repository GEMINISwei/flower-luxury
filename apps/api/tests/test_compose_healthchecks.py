"""探測必須反映服務狀態, 且不能靠反覆啟動應用直譯器。"""

import json
import os
import re
import shutil
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from shared.jobs.health import HEARTBEAT_PATH

ROOT = Path(__file__).resolve().parents[3]
BASH = shutil.which("bash") or "/bin/bash"


def healthchecks():
    result = {}
    for path in (ROOT / "infra/docker").glob("docker-compose*.yml"):
        for service, body in re.findall(r"^  ([\w-]+):\n(.*?)(?=^  \S|^\S|\Z)",
                                        path.read_text(), re.M | re.S):
            match = re.search(r"^    healthcheck:\n((?:      .*\n)+)", body, re.M)
            if match:
                result[service] = dict(re.findall(r"^      (\w+): (.+)$", match[1], re.M))
    return result


def test_healthchecks_only_poll_fast_during_startup():
    checks = healthchecks()
    assert {"api", "web", "postgres", "line-collector"} <= checks.keys()
    for service, fields in checks.items():
        command = json.loads(fields["test"])
        assert not re.search(r"\b(python3?|node|npm|npx)\b", " ".join(command)), service
        assert fields["start_interval"] == "1s", service
        assert fields["interval"] == "30s", service
        assert fields["start_period"] == "60s", service
        assert fields["timeout"] == "5s" and fields["retries"] == "3", service


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(getattr(self.server, "probe_status"))
        self.end_headers()

    def log_message(self, format, *args):
        pass


@pytest.mark.parametrize("service", ["api", "web"])
@pytest.mark.parametrize("status", [200, 204, 301, 401, 503])
def test_http_probe_accepts_only_healthy_response(service, status):
    server = HTTPServer(("127.0.0.1", 0), Handler)
    setattr(server, "probe_status", status)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        command = json.loads(healthchecks()[service]["test"])
        assert command[:3] == ["CMD", "bash", "-c"]
        script = re.sub(r"/dev/tcp/127\.0\.0\.1/\d+",
                        f"/dev/tcp/127.0.0.1/{server.server_port}", command[3])
        result = subprocess.run([BASH, "-c", script], timeout=5, check=False)  # noqa: S603
        assert (result.returncode == 0) == (status == 200)
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.parametrize("service", ["api", "web"])
def test_http_probe_rejects_closed_port(service):
    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_port
    server.server_close()
    command = json.loads(healthchecks()[service]["test"])
    assert command[:3] == ["CMD", "bash", "-c"]
    script = re.sub(r"/dev/tcp/127\.0\.0\.1/\d+", f"/dev/tcp/127.0.0.1/{port}", command[3])
    assert subprocess.run([BASH, "-c", script], timeout=5, check=False).returncode != 0  # noqa: S603


@pytest.mark.parametrize(("age", "healthy"), [(None, False), (-5, False), (5, True), (31, False)])
def test_collector_shell_probe_checks_heartbeat_freshness(tmp_path, age, healthy):
    path = tmp_path / "heartbeat"
    if age is not None:
        path.touch()
        timestamp = time.time() - age
        os.utime(path, (timestamp, timestamp))
    command = json.loads(healthchecks()["line-collector"]["test"])
    assert command[:3] == ["CMD", "bash", "-c"]
    script = command[3].replace(str(HEARTBEAT_PATH), str(path)).replace("$$", "$")
    result = subprocess.run([BASH, "-c", script], timeout=5, check=False)  # noqa: S603
    assert (result.returncode == 0) == healthy
