import subprocess
import sys
from pathlib import Path

import pytest

API_ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(("age", "expected"), [(None, 1), (-5, 1), (5, 0), (31, 1)])
def test_healthcheck_without_application_dependencies_reports_heartbeat(age, expected):
    script = f"""
import pathlib
import runpy
import sys
import time
from types import SimpleNamespace

original_stat = pathlib.Path.stat
def heartbeat_stat(path, *args, **kwargs):
    if str(path) == '/tmp/line-collector-heartbeat':
        age = {age!r}
        if age is None:
            raise FileNotFoundError
        return SimpleNamespace(st_mtime=time.time() - age)
    return original_stat(path, *args, **kwargs)

pathlib.Path.stat = heartbeat_stat
sys.argv = ['shared.jobs.health', '--healthcheck']
try:
    runpy.run_module('shared.jobs.health', run_name='__main__')
except SystemExit:
    assert not any(name.split('.')[0] in
                   {{'sqlalchemy', 'asyncpg', 'PIL', 'pillow_heif', 'bcrypt', 'modules', 'app'}}
                   for name in sys.modules)
    raise
"""
    result = subprocess.run([sys.executable, "-S", "-c", script], cwd=API_ROOT,  # noqa: S603
                            capture_output=True, text=True, check=False)
    assert result.returncode == expected, result.stderr
