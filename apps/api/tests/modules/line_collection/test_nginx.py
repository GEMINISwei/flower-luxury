from pathlib import Path

import pytest

from tests.test_nginx_templates import proxy_locations

NGINX = Path(__file__).resolve().parents[5] / "infra" / "nginx"


@pytest.mark.parametrize("name", ["default.conf.template", "default.dev.conf.template"])
def test_line_webhook_has_exact_public_location(name):
    locations = proxy_locations((NGINX / name).read_text())
    hooks = [(path, value) for path, value in locations if "line" in path]
    assert len(hooks) == 1
    path, value = hooks[0]
    assert path == "= /api/line/webhook"
    assert "limit_except POST" in value and "proxy_pass" in value
    assert "snippets/proxy-headers.conf" in value
    assert all("/api/line/groups" not in path for path, _ in locations)
