import runpy
import shlex
import sys
from pathlib import Path

import coverage
import pytest

from tests.test_stack_scripts import Sandbox


@pytest.fixture
def covered_box(tmp_path: Path) -> Sandbox:
    box = Sandbox(tmp_path)
    box.write_env("development")
    app = box.repo / "apps" / "api"
    app.mkdir(parents=True, exist_ok=True)
    (app / "pyproject.toml").write_text("[tool.coverage.report]\nfail_under = 74\n")
    (app / "probe.py").write_text(
        "def first():\n    value = 1\n    return value\n\n"
        "def second():\n    value = 2\n    return value\n"
    )
    box.tool("uv", f'#!/bin/sh\nshift\nexec {shlex.quote(sys.executable)} -m "$@"\n')
    inputs = tmp_path / "coverage-inputs"
    inputs.mkdir()
    box.exported["COVERAGE_INPUTS"] = str(inputs)
    return box


def measure(box: Sandbox, group: str, function: str) -> None:
    path = Path(box.exported["COVERAGE_INPUTS"]) / f".coverage.{group}"
    recording = coverage.Coverage(data_file=str(path), config_file=False)
    recording.start()
    namespace = runpy.run_path(str(box.repo / "apps" / "api" / "probe.py"))
    namespace[function]()
    recording.stop()
    recording.save()


def test_api_coverage_combines_both_groups_and_keeps_inputs(covered_box: Sandbox) -> None:
    measure(covered_box, "unit", "first")
    measure(covered_box, "integration", "second")
    result = covered_box.run("check", "api-coverage")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "100%" in result.stdout
    assert len(list(Path(covered_box.exported["COVERAGE_INPUTS"]).glob(".coverage.*"))) == 2


def test_api_coverage_enforces_the_original_floor(covered_box: Sandbox) -> None:
    measure(covered_box, "unit", "first")
    measure(covered_box, "integration", "first")
    result = covered_box.run("check", "api-coverage")
    assert result.returncode != 0
    assert "74" in result.stdout


@pytest.mark.parametrize("missing", ["unit", "integration"])
def test_api_coverage_rejects_a_missing_group(covered_box: Sandbox, missing: str) -> None:
    group = "integration" if missing == "unit" else "unit"
    measure(covered_box, group, "first")
    result = covered_box.run("check", "api-coverage")
    assert result.returncode != 0
    assert f".coverage.{missing}" in result.stderr
