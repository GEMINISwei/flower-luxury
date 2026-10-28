from collections.abc import Iterable

from shared.module import ModuleManifest, validate_modules

from .contracts import TaskSpec


def collect_tasks(modules: Iterable[ModuleManifest]) -> dict[str, TaskSpec]:
    return {task.name: task for module in validate_modules(modules) for task in module.tasks}
