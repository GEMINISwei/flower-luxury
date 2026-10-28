import pytest

from shared.jobs.contracts import Job, TaskSpec
from shared.jobs.registry import collect_tasks
from shared.module import ModuleManifest, validate_modules


async def handle(job: Job) -> None:
    pass


def test_duplicate_task_names_are_rejected():
    task = TaskSpec("example.process", handle)
    modules = (ModuleManifest("one", tasks=(task,)), ModuleManifest("two", tasks=(task,)))
    with pytest.raises(RuntimeError, match="duplicate task"):
        validate_modules(modules)


def test_task_registry_follows_enabled_modules():
    first = TaskSpec("one.process", handle)
    second = TaskSpec("two.process", handle)
    modules = (ModuleManifest("one", tasks=(first,)), ModuleManifest("two", tasks=(second,)))
    assert collect_tasks(modules) == {first.name: first, second.name: second}
    assert collect_tasks(modules[:1]) == {first.name: first}
    assert collect_tasks(()) == {}


@pytest.mark.parametrize(("attempts", "timeout"), [(0, 1), (1, 0)])
def test_invalid_task_policy_is_rejected(attempts, timeout):
    with pytest.raises(ValueError):
        TaskSpec("example.process", handle, max_attempts=attempts, timeout_seconds=timeout)
