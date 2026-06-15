"""Centralized configuration for GMA.

Config is loaded from a TOML file with environment variable overrides.
Priority: CLI args > env vars > config file > defaults.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

_DEFAULT_CONFIG_PATH = Path("configs/default.toml")


@dataclass
class AgentConfig:
    profile: str = "default"
    type: str = "basic_e2e"
    model: str = ""
    base_url: str = ""
    api_key: str = ""


@dataclass
class RuntimeConfig:
    device: str = "emulator-5554"
    step_wait_time: float = 1.0
    max_steps: int = 50
    container_image: str = "gma:latest"
    container_prefix: str = "gma_env"


@dataclass
class EvalConfig:
    log_dir: str = "logs"


@dataclass
class UserSimulatorConfig:
    model: str = ""
    base_url: str = ""
    api_key: str = ""
    temperature: float = 0.2
    max_tokens: int = 256
    timeout: float = 60.0
    retries: int = 2


@dataclass
class GMAConfig:
    agent: AgentConfig = field(default_factory=AgentConfig)
    agents: dict[str, AgentConfig] = field(default_factory=dict)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    evaluation: EvalConfig = field(default_factory=EvalConfig)
    user_simulator: UserSimulatorConfig = field(default_factory=UserSimulatorConfig)


def _apply_section(obj, values: dict) -> None:
    for k, v in values.items():
        if hasattr(obj, k):
            setattr(obj, k, v)


def _merge_agent_config(base: AgentConfig, override: AgentConfig) -> AgentConfig:
    return AgentConfig(
        profile=override.profile or base.profile,
        type=override.type or base.type,
        model=override.model or base.model,
        base_url=override.base_url or base.base_url,
        api_key=override.api_key or base.api_key,
    )


def resolve_agent_config(config: GMAConfig, profile: str | None = None) -> AgentConfig:
    """Resolve the selected agent config, optionally through a named profile."""
    selected_profile = profile or config.agent.profile
    if not selected_profile:
        return config.agent

    profile_cfg = config.agents.get(selected_profile)
    if profile_cfg is None:
        if profile is not None:
            available = ", ".join(sorted(config.agents)) or "(none)"
            raise ValueError(
                f"Unknown agent profile: {selected_profile!r}. Available profiles: {available}"
            )
        return config.agent

    return _merge_agent_config(config.agent, profile_cfg)


def _apply_env_overrides(config: GMAConfig) -> None:
    """Override config values with GMA_ prefixed environment variables."""
    env_map = {
        "GMA_AGENT_PROFILE": ("agent", "profile"),
        "GMA_AGENT_TYPE": ("agent", "type"),
        "GMA_AGENT_MODEL": ("agent", "model"),
        "GMA_AGENT_BASE_URL": ("agent", "base_url"),
        "GMA_API_KEY": ("agent", "api_key"),
        "GMA_AGENT_API_KEY": ("agent", "api_key"),
        "GMA_DEVICE": ("runtime", "device"),
        "GMA_STEP_WAIT_TIME": ("runtime", "step_wait_time"),
        "GMA_MAX_STEPS": ("runtime", "max_steps"),
        "GMA_CONTAINER_IMAGE": ("runtime", "container_image"),
        "GMA_LOG_DIR": ("evaluation", "log_dir"),
        "GMA_USER_SIMULATOR_MODEL": ("user_simulator", "model"),
        "GMA_USER_SIMULATOR_BASE_URL": ("user_simulator", "base_url"),
        "GMA_USER_SIMULATOR_API_KEY": ("user_simulator", "api_key"),
        "GMA_USER_SIMULATOR_TEMPERATURE": ("user_simulator", "temperature"),
        "GMA_USER_SIMULATOR_MAX_TOKENS": ("user_simulator", "max_tokens"),
        "GMA_USER_SIMULATOR_TIMEOUT": ("user_simulator", "timeout"),
        "GMA_USER_SIMULATOR_RETRIES": ("user_simulator", "retries"),
    }
    for env_key, (section, attr) in env_map.items():
        value = os.environ.get(env_key)
        if value is not None:
            section_obj = getattr(config, section)
            current = getattr(section_obj, attr)
            # Coerce to the field type
            if isinstance(current, int):
                value = int(value)
            elif isinstance(current, float):
                value = float(value)
            setattr(section_obj, attr, value)
            logger.debug(f"Config override from env: {env_key} -> {section}.{attr}")


def load_config(config_path: str | Path | None = None) -> GMAConfig:
    """Load configuration from TOML file with env var overrides.

    Args:
        config_path: Path to TOML config file.  If None, tries
            ``configs/default.toml`` in the current directory.

    Returns:
        Populated ``GMAConfig`` instance.
    """
    config = GMAConfig()

    if config_path is None:
        config_path = _DEFAULT_CONFIG_PATH
    config_path = Path(config_path)

    if config_path.exists():
        logger.debug(f"Loading config from {config_path}")
        with open(config_path, "rb") as f:
            data = tomllib.load(f)

        # Populate sections
        if "agent" in data:
            _apply_section(config.agent, data["agent"])
        if "agents" in data:
            for profile_name, profile_values in data["agents"].items():
                if not isinstance(profile_values, dict):
                    continue
                profile_config = AgentConfig()
                _apply_section(profile_config, profile_values)
                profile_config.profile = profile_name
                config.agents[profile_name] = profile_config
        if "runtime" in data:
            _apply_section(config.runtime, data["runtime"])
        if "evaluation" in data:
            _apply_section(config.evaluation, data["evaluation"])
        if "user_simulator" in data:
            _apply_section(config.user_simulator, data["user_simulator"])
    else:
        logger.debug(f"Config file not found at {config_path}, using defaults")

    _apply_env_overrides(config)
    return config
