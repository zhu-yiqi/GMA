"""Base agent interface.

Agents observe screenshots and produce actions. The base class is minimal —
no vendor-specific code. Use ``LLMClientMixin`` for OpenAI-compatible API
access.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from loguru import logger
from openai import OpenAI

from gma.runtime.models import Action, Observation


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    @abstractmethod
    def act(self, observation: Observation) -> Action:
        """Given an observation, decide the next action."""
        ...

    def on_task_start(
        self,
        goal: str,
        app_context: dict[str, str] | None = None,
    ) -> None:
        """Called when a new task begins. Store the goal, app context, reset state, etc."""
        pass

    def on_task_end(self) -> None:
        """Called when a task ends. Clean up agent state."""
        pass

    def on_user_response(self, question: str, response: str) -> None:
        """Called after a task-scoped simulated user answers a call_user action."""
        pass

    @property
    def stats(self) -> dict[str, Any]:
        """Return agent statistics (token usage, timing, etc.)."""
        return {}


class LLMClientMixin:
    """Mixin for agents that call OpenAI-compatible chat APIs.

    Provides client setup, retry logic, and token tracking.
    """

    def setup_llm(self, base_url: str, api_key: str, timeout: float = 120.0) -> None:
        self._llm_client = OpenAI(
            base_url=base_url,
            api_key=api_key or "empty",
            timeout=timeout,
        )
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0
        self._total_cached_tokens = 0

    def llm_chat(
        self,
        model: str,
        messages: list[dict],
        retries: int = 3,
        **kwargs,
    ) -> str | None:
        """Call the chat completions API with retries."""
        for attempt in range(retries):
            try:
                resp = self._llm_client.chat.completions.create(
                    model=model, messages=messages, **kwargs,
                )
                self._track_usage(resp)
                return resp.choices[0].message.content.strip()
            except Exception as e:
                logger.warning(f"LLM call failed (attempt {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    time.sleep(1)
        return None

    def _track_usage(self, response) -> None:
        if response.usage is None:
            return
        self._total_prompt_tokens += response.usage.prompt_tokens or 0
        self._total_completion_tokens += response.usage.completion_tokens or 0
        if hasattr(response.usage, "prompt_tokens_details") and response.usage.prompt_tokens_details:
            self._total_cached_tokens += response.usage.prompt_tokens_details.cached_tokens or 0

    def llm_stats(self) -> dict[str, int]:
        return {
            "prompt_tokens": self._total_prompt_tokens,
            "completion_tokens": self._total_completion_tokens,
            "cached_tokens": self._total_cached_tokens,
            "total_tokens": self._total_prompt_tokens + self._total_completion_tokens,
        }

    def reset_llm_stats(self) -> None:
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0
        self._total_cached_tokens = 0
