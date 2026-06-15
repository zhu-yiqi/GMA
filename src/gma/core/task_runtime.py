"""Task lifecycle helpers for CLI-driven manual and agent runs."""

from __future__ import annotations

from dataclasses import dataclass

from gma.runtime.client import GMAClient
from gma.runtime.docker import discover_containers
from gma.tasks.base import BaseTask
from gma.tasks.registry import TaskRegistry


@dataclass
class TaskContext:
    task: BaseTask | None
    client: GMAClient
    url: str
    device: str
    container_name: str | None = None


def resolve_client(url: str | None = None, device: str = "emulator-5554") -> TaskContext | None:
    if url is None:
        containers = discover_containers()
        if not containers:
            return None
        chosen = containers[0]
        url = chosen["backend_url"]
        container_name = chosen["name"]
    else:
        container_name = None

    client = GMAClient(url, device=device)
    client.init()
    return TaskContext(
        task=None,  # filled by attach_task()
        client=client,
        url=url,
        device=device,
        container_name=container_name,
    )


def load_task(
    task_name: str,
    extra_task_dirs: list[str] | None = None,
    *,
    include_builtin: bool = True,
) -> BaseTask:
    registry = TaskRegistry(*(extra_task_dirs or []), include_builtin=include_builtin)
    return registry.get(task_name)


def attach_task(
    task_name: str,
    url: str | None = None,
    device: str = "emulator-5554",
    extra_task_dirs: list[str] | None = None,
) -> TaskContext | None:
    context = resolve_client(url=url, device=device)
    if context is None:
        return None
    context.task = load_task(task_name, extra_task_dirs=extra_task_dirs)
    return context
