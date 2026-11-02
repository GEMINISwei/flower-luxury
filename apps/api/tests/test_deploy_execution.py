import re
import shlex
import shutil
import subprocess
import textwrap

import pytest

from tests.test_stack_scripts import BASH, REPO_ROOT, Sandbox

WORKFLOW = REPO_ROOT / ".github/workflows/deploy.yml"
VERIFIER = ".github/scripts/verify-deployment.sh"


def deployment_command() -> str:
    workflow = WORKFLOW.read_text()
    step = re.search(r"^      - name: 部署到主機\n(.*?)(?=^  \S|\Z)", workflow,
                     flags=re.MULTILINE | re.DOTALL)
    assert step is not None
    body = step.group(1).split("        run: |\n", 1)[1]
    return textwrap.dedent(body)


@pytest.fixture
def deployment(tmp_path):
    sandbox = Sandbox(tmp_path)
    sandbox.write_env("production")
    (sandbox.repo / "apps/api/app/config.py").write_text('APP_VERSION = "1.2.3"\n')
    if (REPO_ROOT / VERIFIER).exists():
        target = sandbox.repo / VERIFIER
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO_ROOT / VERIFIER, target)
    state = shlex.quote(str(sandbox.state))
    sandbox.tool("ssh", f"#!/bin/sh\nexec {shlex.quote(BASH)} -s\n")
    sandbox.tool("git", f'''#!/bin/sh
printf 'git %s\\n' "$*" >> {state}/commands
''')
    sandbox.tool("make", f'''#!/bin/sh
printf 'make %s\\n' "$*" >> {state}/commands
# Model an attached Docker client, which may consume the remaining SSH script.
[ "$*" != "${{DRAIN_MAKE:-start}}" ] || cat > {state}/consumed-input
[ "$*" != "${{FAILED_MAKE:-}}" ] || exit 7
''')
    sandbox.tool("sleep", f"#!/bin/sh\nprintf 'sleep\\n' >> {state}/commands\n")
    sandbox.tool("docker", docker_tool(state))
    return sandbox


def docker_tool(state: str) -> str:
    return f'''#!/bin/sh
state={state}
printf 'docker %s\\n' "$*" >> "$state/commands"
for last in "$@"; do :; done
case "$1" in
    login) cat >/dev/null ;;
    inspect)
        case "$3" in
            *State*)
                health=healthy
                if [ "$last" = my-app-line-collector ]; then
                    health="${{WORKER_STATE:-healthy}}"
                    [ "$health" != missing ] || exit 1
                    if [ "$health" = starting_once ]; then
                        if [ -f "$state/polled" ]; then health=healthy
                        else health=starting; touch "$state/polled"; fi
                    fi
                fi
                if [ "$last" = my-app-nginx ]; then printf 'running\\n'
                elif [ "$health" = exited ]; then printf 'exited\\n'
                else printf 'running %s\\n' "$health"; fi ;;
            *Image*)
                if [ "$last" = my-app-line-collector ]; then
                    echo "${{RUNTIME_WORKER_IMAGE:-current-image}}"
                else echo current-image; fi ;;
            *) exit 2 ;;
        esac ;;
    exec) echo "${{RUNTIME_API_VERSION:-1.2.3}}" ;;
    image) exit 0 ;;
    *) exit 2 ;;
esac
'''


def run_deployment(sandbox: Sandbox, **extra: str) -> subprocess.CompletedProcess[str]:
    environment = {
        **sandbox.env(), "DEPLOY_HOST": "fixture.invalid", "DEPLOY_PORT": "22",
        "DEPLOY_USER": "fixture", "DEPLOY_PATH": str(sandbox.repo), "BACKUP_KEEP": "10",
        "GITHUB_TOKEN": "private-fixture-token", "GITHUB_ACTOR": "fixture", "TAG": "v1.2.3",
        "API_IMAGE": "fixture-api:production", "WEB_IMAGE": "fixture-web:production", **extra,
    }
    return subprocess.run(  # noqa: S603
        [BASH, "-c", deployment_command()], cwd=sandbox.repo, env=environment,
        capture_output=True, text=True, check=False, timeout=15,
    )


def commands(sandbox: Sandbox) -> list[str]:
    path = sandbox.state / "commands"
    return path.read_text().splitlines() if path.exists() else []


@pytest.mark.parametrize("reader", ["start", "backup allow-fresh", "services"])
def test_deploy_preserves_post_start_checks_when_child_reads_stdin(deployment, reader):
    result = run_deployment(deployment, DRAIN_MAKE=reader)
    assert result.returncode == 0, result.stdout + result.stderr
    calls = commands(deployment)
    assert [line for line in calls if line.startswith("make ")] == [
        "make backup allow-fresh", "make start", "make services", "make backup prune 10"]
    assert "v1.2.3" in result.stdout and "line-collector" in result.stdout
    assert "healthy" in result.stdout
    assert "private-fixture-token" not in result.stdout + result.stderr
    assert (deployment.state / "consumed-input").read_text() == ""


def test_deploy_start_failure_stops_verification_and_cleanup(deployment):
    result = run_deployment(deployment, FAILED_MAKE="start")
    assert result.returncode != 0 and "啟動服務失敗" in result.stdout
    assert "make services" not in commands(deployment)
    assert not any("image prune" in line for line in commands(deployment))


@pytest.mark.parametrize("state", ["unhealthy", "exited", "missing", "starting"])
def test_deploy_rejects_unhealthy_or_missing_worker_before_cleanup(deployment, state):
    result = run_deployment(deployment, WORKER_STATE=state)
    assert result.returncode != 0
    assert "::error::" in result.stdout + result.stderr
    assert "make backup prune 10" not in commands(deployment)


def test_deploy_waits_for_starting_worker_to_become_healthy(deployment):
    result = run_deployment(deployment, WORKER_STATE="starting_once")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "sleep" in commands(deployment)
    assert "make backup prune 10" in commands(deployment)


def test_deploy_rejects_runtime_version_mismatch(deployment):
    result = run_deployment(deployment, RUNTIME_API_VERSION="1.2.2")
    assert result.returncode != 0 and "1.2.2" in result.stdout + result.stderr
    assert "make backup prune 10" not in commands(deployment)


def test_deploy_rejects_worker_image_different_from_api(deployment):
    result = run_deployment(deployment, RUNTIME_WORKER_IMAGE="old-image")
    assert result.returncode != 0
    assert "make backup prune 10" not in commands(deployment)


def test_deploy_cleanup_failure_warns_after_successful_verification(deployment):
    result = run_deployment(deployment, FAILED_MAKE="backup prune 10")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "v1.2.3" in result.stdout
    assert "::warning::清理舊備份失敗" in result.stdout
    assert any("image prune" in line for line in commands(deployment))
