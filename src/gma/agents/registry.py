"""Agent discovery and instantiation."""

from __future__ import annotations

import importlib.util
import inspect
import sys
from pathlib import Path

from loguru import logger

from gma.agents.base import BaseAgent

# Built-in agent types.  Populated as agent implementations are added.
AGENT_REGISTRY: dict[str, type[BaseAgent]] = {}


def register_agent(name: str, cls: type[BaseAgent]) -> None:
    """Register an agent class under the given name."""
    AGENT_REGISTRY[name] = cls


def create_agent(agent_type: str, **kwargs) -> BaseAgent:
    """Create an agent by registered name or by file path.

    If ``agent_type`` ends with ``.py`` or is an existing file path, the
    agent class is loaded dynamically from that file.  Otherwise it is
    looked up in the registry.
    """
    if agent_type.endswith(".py") or Path(agent_type).is_file():
        cls = _load_agent_from_file(agent_type)
    elif agent_type in AGENT_REGISTRY:
        cls = AGENT_REGISTRY[agent_type]
    else:
        available = list(AGENT_REGISTRY.keys())
        raise ValueError(f"Unknown agent type: {agent_type!r}. Available: {available}")
    return cls(**kwargs)


def list_agents() -> list[str]:
    """Return names of all registered agents."""
    return sorted(AGENT_REGISTRY.keys())


def _load_agent_from_file(file_path: str) -> type[BaseAgent]:
    """Load an agent class from a Python file."""
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Agent file not found: {path}")

    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = module
    spec.loader.exec_module(module)

    candidates = [
        obj for _, obj in inspect.getmembers(module, inspect.isclass)
        if issubclass(obj, BaseAgent) and obj is not BaseAgent
    ]
    if not candidates:
        raise ValueError(f"No BaseAgent subclass found in {path}")
    if len(candidates) > 1:
        names = [c.__name__ for c in candidates]
        logger.warning(f"Multiple agents in {path}: {names}. Using {names[0]}")
    return candidates[0]
