import re

import pytest

from tests.test_stack_scripts import (
    ALL_RUNNING,
    NGINX,
    PROJECT,
    REPO_ROOT,
    Sandbox,
    existing_backup,
    running_production,
)

COLLECTOR = f"{PROJECT}-line-collector"


@pytest.fixture
def collector_box(tmp_path):
    box = Sandbox(tmp_path)
    running_production(box)
    box.containers(*ALL_RUNNING, COLLECTOR)
    return box


def test_backup_stops_worker_and_restores_previous_state(collector_box):
    box = collector_box
    result = box.run("backup")
    assert result.returncode == 0, result.stderr
    assert box.first(f"stop {COLLECTOR}") < box.first("pg_dump")
    assert box.first(" -cf ") < box.first(f"start {COLLECTOR}")
    assert box.first(f"stop {NGINX}") < box.first("pg_dump")


def test_backup_failure_restores_worker(collector_box):
    box = collector_box
    box.fail("pg_dump")
    result = box.run("backup")
    assert result.returncode != 0
    assert box.first(f"stop {COLLECTOR}") < box.first(f"start {COLLECTOR}")
    assert box.called(f"start {NGINX}")


@pytest.mark.parametrize("nginx_running", [True, False])
def test_stopped_worker_is_not_started_by_backup(collector_box, nginx_running):
    box = collector_box
    box.containers(*(name for name in ALL_RUNNING if nginx_running or name != NGINX))
    assert box.run("backup").returncode == 0
    assert not box.called(f"stop {COLLECTOR}")
    assert not box.called(f"start {COLLECTOR}")


def test_backup_stops_worker_even_when_nginx_is_stopped(collector_box):
    box = collector_box
    box.containers(*(name for name in ALL_RUNNING if name != NGINX), COLLECTOR)
    assert box.run("backup").returncode == 0
    assert box.first(f"stop {COLLECTOR}") < box.first("pg_dump")
    assert box.called(f"start {COLLECTOR}")
    assert not box.called(f"start {NGINX}")


@pytest.mark.parametrize(("script", "extension", "restore"), [
    ("db", "dump", "pg_restore"), ("uploads", "tar", " -xf "),
])
def test_restore_keeps_worker_stopped_until_finished(collector_box, script, extension, restore):
    box = collector_box
    file = existing_backup(box, extension)
    result = box.run(script, "restore", file, answer="y\n")
    assert result.returncode == 0, result.stderr
    assert box.first(f"stop {COLLECTOR}") < box.first("pg_dump")
    assert box.first(" -cf ") < box.first(restore) < box.first(f"start {COLLECTOR}")
    assert sum(call == f"start {COLLECTOR}" for call in box.calls()) == 1


@pytest.mark.parametrize("mode", ["development", "production"])
def test_migration_runs_with_worker_stopped(collector_box, mode):
    box = collector_box
    box.write_env(mode)
    box.release_checkout()
    result = box.run("start")
    assert result.returncode == 0, result.stderr
    assert box.first(f"stop {COLLECTOR}") < box.first(" migrate") < box.first(" up ")


def test_migration_failure_restores_previous_worker(collector_box):
    box = collector_box
    box.release_checkout()
    box.fail("migrate")
    result = box.run("start")
    assert result.returncode != 0
    assert not box.called(" up ")
    assert box.first(f"stop {COLLECTOR}") < box.first(f"start {COLLECTOR}")


@pytest.mark.parametrize("command", ["migrate", "reset"])
def test_manual_database_changes_stop_worker(collector_box, command):
    box = collector_box
    box.write_env("development")
    result = box.run("db", command, answer="y\n")
    assert result.returncode == 0, result.stderr
    assert box.first(f"stop {COLLECTOR}") < box.first(f"scripts/db.py {command}")
    assert box.last("scripts/db.py migrate") < box.first(f"start {COLLECTOR}")


def test_worker_stop_failure_aborts_backup(collector_box):
    box = collector_box
    box.fail(COLLECTOR)
    assert box.run("backup").returncode != 0
    assert not box.called("pg_dump")
    assert box.called(f"start {NGINX}")


def test_collector_compose_uses_api_runtime():
    text = (REPO_ROOT / "infra/docker/docker-compose.yml").read_text()
    match = re.search(r"^  line-collector:\n(.*?)(?=^  \S|^\S|\Z)", text, re.M | re.S)
    assert match is not None
    service = match.group(1)
    assert "<<: *api-image" in service
    assert "${COMPOSE_PROJECT_NAME:?}-line-collector" in service
    assert "uploads:/app/uploads" in service
    assert 'command: ["python", "-m", "app.collector"]' in service
    assert "service_completed_successfully" in service
    assert "--healthcheck" in service
    assert "stop_grace_period:" in service
    assert "ports:" not in service and "expose:" not in service
    dev = (REPO_ROOT / "infra/docker/docker-compose.dev.yml").read_text()
    assert re.search(r"line-collector:\n\s+volumes: \*api-source", dev)
    prod = (REPO_ROOT / "infra/docker/docker-compose.prod.yml").read_text()
    assert re.search(r"line-collector:\n\s+<<: \*prod-runtime", prod)
