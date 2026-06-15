"""Shared data models for actions, observations, and server requests."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, field_validator, model_validator


class ActionType(StrEnum):
    """All possible agent actions."""

    CLICK = "click"
    DOUBLE_TAP = "double_tap"
    LONG_PRESS = "long_press"
    SCROLL = "scroll"
    INPUT_TEXT = "input_text"
    NAVIGATE_HOME = "navigate_home"
    NAVIGATE_BACK = "navigate_back"
    KEYBOARD_ENTER = "keyboard_enter"
    OPEN_APP = "open_app"
    DRAG = "drag"
    CALL_USER = "call_user"
    ANSWER = "answer"
    STATUS = "status"
    WAIT = "wait"


# Actions that signal task termination
TERMINAL_ACTIONS = {ActionType.ANSWER, ActionType.STATUS}

# Valid scroll directions
SCROLL_DIRECTIONS = {"up", "down", "left", "right"}


class Action(BaseModel):
    """Agent action sent to the environment.

    Fields are type-dependent — e.g. ``x``/``y`` are only used by click,
    ``text`` by input_text/call_user/answer, ``direction`` by scroll, etc.
    """

    action_type: ActionType
    x: int | None = None
    y: int | None = None
    text: str | None = None
    direction: str | None = None
    goal_status: str | None = None
    app_name: str | None = None
    start_x: int | None = None
    start_y: int | None = None
    end_x: int | None = None
    end_y: int | None = None

    @field_validator("x", "y", "start_x", "start_y", "end_x", "end_y", mode="before")
    @classmethod
    def round_coordinates(cls, v: int | float | None) -> int | None:
        if v is not None:
            return round(v)
        return v

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v: str | None) -> str | None:
        if v is not None and v not in SCROLL_DIRECTIONS:
            raise ValueError(f"Invalid direction: {v!r}. Must be one of {SCROLL_DIRECTIONS}")
        return v

    @field_validator("text", mode="before")
    @classmethod
    def coerce_text(cls, v: Any) -> str | None:
        if v is not None and not isinstance(v, str):
            return str(v)
        return v

    @model_validator(mode="after")
    def check_coordinate_exclusivity(self):
        """Click/tap actions should not mix index-style and coordinate-style addressing."""
        return self

    @property
    def is_terminal(self) -> bool:
        return self.action_type in TERMINAL_ACTIONS


class Observation(BaseModel):
    """What the agent receives each step."""

    screenshot: Any  # PIL.Image.Image — kept as Any to avoid import cost
    metadata: dict[str, Any] = {}


# --- Server request/response models ---


class InitRequest(BaseModel):
    device: str = "emulator-5554"


class StepRequest(BaseModel):
    device: str
    action: Action


class TaskRequest(BaseModel):
    task_name: str
    device: str = "emulator-5554"
