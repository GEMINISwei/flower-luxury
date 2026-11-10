import shlex
import shutil

import pytest

from tests.test_stack_scripts import REPO_ROOT, Sandbox


@pytest.fixture
def checks(tmp_path):
    sandbox = Sandbox(tmp_path)
    sandbox.write_env("development")
    compose = sandbox.repo / "infra/docker/docker-compose.yml"
    compose.parent.mkdir(parents=True)
    shutil.copy(REPO_ROOT / "infra/docker/docker-compose.yml", compose)
    # integration 跑完會從 pyproject 讀覆蓋率門檻, 再跟假 uv 回傳的總計比對。
    shutil.copy(REPO_ROOT / "apps/api/pyproject.toml", sandbox.repo / "apps/api")
    for relative in ("contracts/openapi.json", "apps/web/shared/api/generated/schema.d.ts"):
        path = sandbox.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n")
    state = shlex.quote(str(sandbox.state))
    sandbox.tool("docker", f'''#!/bin/sh
state={state}
printf '%s\\n' "$*" >> "$state/calls"
case "$1" in port) echo 127.0.0.1:54321 ;; esac
exit 0
''')
    sandbox.tool("uv", f'''#!/bin/sh
state={state}
printf '%s|db=%s|required=%s\\n' "$*" "${{POSTGRES_URL:-}}" \
    "${{REQUIRE_INTEGRATION:-}}" >> "$state/uv"
case "$*" in
    *pytest*)
        [ -e "$state/fail-pytest" ] && exit 1
        echo '1 passed' ;;
    *'coverage report --format=total'*) echo 100.00 ;;
    *'alembic check'*) [ ! -e "$state/fail-migration" ] || exit 1 ;;
    *export_openapi*) for last in "$@"; do :; done; printf '{{}}\\n' > "$last" ;;
esac
exit 0
''')
    sandbox.tool("npm", f'''#!/bin/sh
printf '%s\\n' "$*" >> {state}/npm
case "$*" in *build*) echo 'ƒ Proxy (Middleware)' ;; esac
exit 0
''')
    sandbox.tool("npx", '''#!/bin/sh
for last in "$@"; do :; done
printf '{}\\n' > "$last"
''')
    sandbox.tool("git", '''#!/bin/sh
case "$*" in *describe*) exit 1 ;; *hooksPath*) echo .githooks ;; esac
''')
    sandbox.tool("shellcheck", "#!/bin/sh\nexit 0\n")
    return sandbox


def test_integration_uses_disposable_database_and_cleans_container(checks):
    result = checks.run("check", "integration")
    assert result.returncode == 0, result.stdout + result.stderr
    calls = checks.calls()
    assert any(call.startswith("run -d --name my-app-test-postgres") for call in calls)
    assert sum(call == "rm -f my-app-test-postgres" for call in calls) == 2
    commands = (checks.state / "uv").read_text()
    assert "run pytest tests/ -q -m integration" in commands
    assert "db=postgresql+asyncpg://test:test@127.0.0.1:54321/test|required=1" in commands
    assert "alembic upgrade head" in commands and "alembic check" in commands
    assert not (checks.state / "npm").exists()


@pytest.mark.parametrize("failure", ["pytest", "migration"])
def test_integration_failure_cleans_container(checks, failure):
    checks.fail(failure)
    result = checks.run("check", "integration")
    assert result.returncode != 0
    assert checks.calls()[-1] == "rm -f my-app-test-postgres"
    assert not (checks.state / "npm").exists()


def test_quick_tests_do_not_start_database(checks):
    result = checks.run("check", "test")
    assert result.returncode == 0, result.stdout + result.stderr
    assert checks.calls() == []
    assert "required=1" in (checks.state / "uv").read_text()
