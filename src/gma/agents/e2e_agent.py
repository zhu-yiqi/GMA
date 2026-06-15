from __future__ import annotations

import base64
import json
from io import BytesIO
from typing import Any

from loguru import logger

from gma.agents.base import BaseAgent, LLMClientMixin
from gma.agents.registry import register_agent
from gma.runtime.models import Action, ActionType

ACTION_ALIASES = {
    "click": ["tap", "press", "touch"],
    "long_press": ["hold", "long tap"],
    "input_text": ["type", "enter_text", "write", "enter"],
    "scroll": ["swipe", "fling"],
    "navigate_home": ["home"],
    "navigate_back": ["back"],
    "keyboard_enter": ["enter_key"],
    "open_app": ["open", "launch_app", "launch"],
    "call_user": ["ask_user", "ask user", "clarify", "ask"],
    "wait": ["pause"],
    "status": ["finish", "terminate"],
}

NORMALIZED_ACTIONS: dict[str, str] = {}
for canonical, aliases in ACTION_ALIASES.items():
    NORMALIZED_ACTIONS[canonical] = canonical
    for alias in aliases:
        NORMALIZED_ACTIONS[alias] = canonical
        NORMALIZED_ACTIONS[alias.replace(" ", "_")] = canonical

SYSTEM_PROMPT = """You are a mobile GUI agent operating an Android phone from screenshots.

You must output exactly:
Thought: <one concise sentence>
Action: <one JSON object>

Allowed actions:
- {"action_type":"click","coordinate":[x,y]}
- {"action_type":"double_tap","coordinate":[x,y]}
- {"action_type":"long_press","coordinate":[x,y]}
- {"action_type":"drag","start_coordinate":[x1,y1],"end_coordinate":[x2,y2]}
- {"action_type":"scroll","direction":"up|down|left|right"}
- {"action_type":"input_text","text":"..."}
- {"action_type":"keyboard_enter"}
- {"action_type":"navigate_home"}
- {"action_type":"navigate_back"}
- {"action_type":"open_app","app_name":"package or app name"}
- {"action_type":"call_user","text":"question for the user"}
- {"action_type":"wait"}
- {"action_type":"answer","text":"final answer"}
- {"action_type":"status","goal_status":"complete|infeasible"}

Rules:
- Screen coordinates are relative on a 0-1000 scale, where [0,0] is top-left and [1000,1000] is bottom-right.
- Only output one action each turn.
- Use status complete only when the task is done.
- Use status infeasible only when the task cannot be completed.
- When you believe the task is fully completed, your next action must be {"action_type":"status","goal_status":"complete"}.
- For tasks that ask you to report an answer rather than change the UI, use {"action_type":"answer","text":"..."} as the final action.
- Do not continue interacting with the phone after the task is complete.
- If you need to type text, assume the field is already focused only if it clearly is; otherwise click it first.
- If the screen is loading or transitioning, use wait.
- Use call_user when the goal is ambiguous or missing necessary information. Do not guess required user preferences that are not in the task goal.
- Prefer the shortest reliable path.
"""


def _pil_to_data_url(image) -> str:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _parse_json_fragment(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            stripped = "\n".join(lines[1:-1]).strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            return json.loads(stripped[start:end + 1])
        raise


def _split_response(text: str) -> tuple[str, str]:
    if "Action:" not in text:
        raise ValueError("Model response missing 'Action:' section")
    thought_part, action_part = text.split("Action:", 1)
    thought = thought_part.replace("Thought:", "", 1).strip()
    action = action_part.strip()
    return thought, action


def _normalize_action_type(action_type: str | None) -> str | None:
    if not action_type:
        return None
    key = action_type.lower().strip().replace(" ", "_")
    return NORMALIZED_ACTIONS.get(key, key)


def _to_absolute(x: float, y: float, width: int, height: int, scale: int) -> tuple[int, int]:
    return int(x * width / scale), int(y * height / scale)


def _action_from_dict(data: dict[str, Any], width: int, height: int, scale_factor: int) -> Action:
    action_type = _normalize_action_type(data.get("action_type"))
    if not action_type:
        raise ValueError("Missing action_type")

    if action_type in {"click", "double_tap", "long_press"}:
        coord = data.get("coordinate")
        if not isinstance(coord, list) or len(coord) != 2:
            raise ValueError(f"{action_type} requires coordinate [x, y]")
        x, y = _to_absolute(coord[0], coord[1], width, height, scale_factor)
        return Action(action_type=ActionType(action_type), x=x, y=y)

    if action_type == "drag":
        start = data.get("start_coordinate")
        end = data.get("end_coordinate")
        if not isinstance(start, list) or len(start) != 2 or not isinstance(end, list) or len(end) != 2:
            raise ValueError("drag requires start_coordinate and end_coordinate")
        start_x, start_y = _to_absolute(start[0], start[1], width, height, scale_factor)
        end_x, end_y = _to_absolute(end[0], end[1], width, height, scale_factor)
        return Action(
            action_type=ActionType.DRAG,
            start_x=start_x,
            start_y=start_y,
            end_x=end_x,
            end_y=end_y,
        )

    if action_type == "scroll":
        return Action(action_type=ActionType.SCROLL, direction=str(data.get("direction", "down")))

    if action_type == "input_text":
        return Action(action_type=ActionType.INPUT_TEXT, text=str(data.get("text", "")))

    if action_type == "open_app":
        return Action(action_type=ActionType.OPEN_APP, app_name=str(data.get("app_name", "")))

    if action_type == "answer":
        return Action(action_type=ActionType.ANSWER, text=str(data.get("text", "")))

    if action_type == "call_user":
        return Action(action_type=ActionType.CALL_USER, text=str(data.get("text", "")))

    if action_type == "status":
        goal_status = str(data.get("goal_status", "")).strip().lower()
        if goal_status == "fail":
            goal_status = "infeasible"
        if goal_status not in {"complete", "infeasible"}:
            raise ValueError(f"Invalid goal_status: {goal_status}")
        return Action(action_type=ActionType.STATUS, goal_status=goal_status)

    if action_type in {"wait", "navigate_home", "navigate_back", "keyboard_enter"}:
        return Action(action_type=ActionType(action_type))

    raise ValueError(f"Unsupported action type: {action_type}")


class BasicE2EAgent(BaseAgent, LLMClientMixin):
    def __init__(
        self,
        model_name: str,
        llm_base_url: str,
        api_key: str = "empty",
        runtime_conf: dict[str, Any] | None = None,
        scale_factor: int = 1000,
        history_n_images: int = 3,
        **_: Any,
    ):
        self.model_name = model_name
        self.llm_base_url = llm_base_url
        self.api_key = api_key
        self.runtime_conf = {
            "temperature": 0.0,
            "max_tokens": 1024,
        }
        if runtime_conf:
            self.runtime_conf.update(runtime_conf)
        self.scale_factor = scale_factor
        self.history_n_images = history_n_images
        self._goal = ""
        self._app_context: dict[str, str] = {}
        self._history: list[dict[str, Any]] = []
        self._responses: list[str] = []
        self._user_turns: list[dict[str, str]] = []
        self.setup_llm(llm_base_url, api_key)

    def on_task_start(self, goal: str, app_context: dict[str, str] | None = None) -> None:
        self._goal = goal
        self._app_context = dict(app_context or {})
        self._history = []
        self._responses = []
        self._user_turns = []
        self.reset_llm_stats()

    def on_task_end(self) -> None:
        self._goal = ""
        self._app_context = {}
        self._history = []
        self._responses = []
        self._user_turns = []

    def on_user_response(self, question: str, response: str) -> None:
        self._user_turns.append({"question": question, "response": response})

    def _build_messages(self, observation) -> list[dict[str, Any]]:
        current_image = {
            "type": "image_url",
            "image_url": {"url": _pil_to_data_url(observation.screenshot)},
        }
        app_lines = ""
        if self._app_context:
            formatted = "\n".join(
                f"- {app_name}: {package}"
                for app_name, package in sorted(self._app_context.items())
            )
            app_lines = (
                "\nAvailable apps for this task (use these exact app names or packages with open_app):\n"
                f"{formatted}\n"
                "Do not invent other package names."
            )
        user_lines = ""
        if self._user_turns:
            formatted_turns = "\n".join(
                f"- Agent asked: {turn['question']}\n"
                f"  User answered: {turn['response'] or '[no response]'}"
                for turn in self._user_turns[-6:]
            )
            user_lines = (
                "\nUser interaction history from call_user:\n"
                f"{formatted_turns}\n"
                "Use these answers as authoritative task information."
            )
        intro = {
            "role": "system",
            "content": SYSTEM_PROMPT + f"\nCurrent task goal: {self._goal}{app_lines}{user_lines}",
        }
        messages: list[dict[str, Any]] = [intro]

        recent_history = self._history[-self.history_n_images :]
        recent_responses = self._responses[-self.history_n_images :]
        history_pairs = list(zip(recent_history, recent_responses, strict=False))
        for item, resp in history_pairs:
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": item["caption"]},
                    {"type": "image_url", "image_url": {"url": item["data_url"]}},
                ],
            })
            messages.append({
                "role": "assistant",
                "content": resp,
            })

        step_caption = f"Current screen. Goal: {self._goal}. Choose the next single action."
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": step_caption},
                current_image,
            ],
        })
        return messages

    def act(self, observation) -> Action:
        width, height = observation.screenshot.size
        messages = self._build_messages(observation)
        response = self.llm_chat(
            model=self.model_name,
            messages=messages,
            **self.runtime_conf,
        )
        if not response:
            logger.warning("LLM returned no response; waiting")
            return Action(action_type=ActionType.WAIT)

        try:
            thought, action_blob = _split_response(response)
            action_dict = _parse_json_fragment(action_blob)
            action = _action_from_dict(action_dict, width, height, self.scale_factor)
            logger.info(f"Thought: {thought}")
            logger.info(f"Action: {action_dict}")
        except Exception as e:
            logger.warning(f"Failed to parse model response, waiting instead: {e}")
            logger.debug(response)
            action = Action(action_type=ActionType.WAIT)

        self._history.append(
            {
                "caption": f"Previous screen for task: {self._goal}",
                "data_url": _pil_to_data_url(observation.screenshot),
            }
        )
        self._responses.append(response)
        return action

    @property
    def stats(self) -> dict[str, Any]:
        return self.llm_stats()


register_agent("basic_e2e", BasicE2EAgent)
