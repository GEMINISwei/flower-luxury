import re
from pathlib import Path

from shared.jobs.health import HEARTBEAT_PATH

ROOT = Path(__file__).resolve().parents[3]


def test_collector_healthcheck_uses_shell_heartbeat_probe():
    text = (ROOT / "infra/docker/docker-compose.yml").read_text()
    service = text.split("  line-collector:\n", 1)[1].split("\n  postgres:", 1)[0]
    assert '["CMD", "bash",' in service
    assert str(HEARTBEAT_PATH) in service
    assert "--healthcheck" in service
    assert "interval: 30s" in service


def test_collector_production_limits_cpu_and_memory():
    text = (ROOT / "infra/docker/docker-compose.prod.yml").read_text()
    service = text.split("  line-collector:\n", 1)[1].split("\n  postgres:", 1)[0]
    assert re.search(r'cpus:\s*[\"\']?0\.5[\"\']?\s', service)
    assert "memory: 512M" in service
    assert "cpu_shares: 256" in service
