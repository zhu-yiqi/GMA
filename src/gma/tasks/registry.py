"""Auto-scanning task registry.

Scans a directory tree for Python files containing ``BaseTask`` subclasses
and registers them by class name.  Also accepts external directories so
users can add tasks without modifying the package.
"""

from __future__ import annotations

import importlib.util
import inspect
import sys
from pathlib import Path

from loguru import logger


class TaskRegistry:
    """Discovers and holds all available tasks."""

    def __init__(self, *scan_dirs: str | Path, include_builtin: bool = True):
        self._tasks: dict[str, object] = {}

        builtin = Path(__file__).parent / "definitions"
        if include_builtin and builtin.exists():
            self._scan(builtin)

        # Scan additional user-provided directories
        for d in scan_dirs:
            p = Path(d)
            if p.exists():
                self._scan(p)
            else:
                logger.warning(f"Task directory not found: {d}")

        logger.info(f"TaskRegistry: {len(self._tasks)} task(s) registered")

    def _scan(self, directory: Path) -> None:
        """Recursively scan a directory for BaseTask subclasses."""
        from gma.tasks.base import BaseTask

        for py_file in sorted(directory.rglob("*.py")):
            if py_file.name.startswith("_"):
                continue
            try:
                module = self._load_module(py_file)
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (
                        issubclass(obj, BaseTask)
                        and obj is not BaseTask
                        and obj.__module__ == module.__name__
                    ):
                        instance = obj()
                        if name in self._tasks:
                            logger.warning(f"Task {name} already registered, overwriting")
                        self._tasks[name] = instance
            except Exception as e:
                logger.error(f"Failed to load {py_file}: {e}")

    def _load_module(self, file_path: Path):
        """Load a Python module from a file path."""
        module_name = file_path.stem
        # Avoid collisions by using full path as module name
        unique_name = str(file_path).replace("/", ".").replace("\\", ".").removesuffix(".py")
        spec = importlib.util.spec_from_file_location(unique_name, file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module from {file_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[unique_name] = module
        spec.loader.exec_module(module)
        return module

    def get(self, name: str):
        """Get a task by class name. Raises KeyError if not found."""
        if name not in self._tasks:
            raise KeyError(f"Task '{name}' not found. Available: {list(self._tasks.keys())}")
        return self._tasks[name]

    def list_tasks(self) -> list[dict]:
        """Return metadata for all registered tasks."""
        return [
            {
                "name": t.name,
                "goal": t.goal,
                "apps": sorted(t.apps),
                "tags": sorted(t.tags),
            }
            for t in self._tasks.values()
        ]

    def list_names(self) -> list[str]:
        return sorted(self._tasks.keys())

    def has(self, name: str) -> bool:
        return name in self._tasks

    def __len__(self) -> int:
        return len(self._tasks)
