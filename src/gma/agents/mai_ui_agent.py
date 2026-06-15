from __future__ import annotations

import base64
import json
import os
import re
from io import BytesIO
from typing import Any

from loguru import logger

from gma.agents.base import BaseAgent, LLMClientMixin
from gma.agents.registry import register_agent
from gma.runtime.models import Action, ActionType

SCALE_FACTOR = 999

MAI_UI_SYSTEM_PROMPT = """You are a GUI agent operating an Android phone from screenshots.
You are given a task, action history, and screenshots. Choose the next single action.

## Output Format
For each step, return your thinking process in <thinking></thinking> tags and one JSON tool call in <tool_call></tool_call> tags:
<thinking>
A concise analysis ending with the next action target.
</thinking>
<tool_call>
{"name": "mobile_use", "arguments": <args-json-object>}
</tool_call>

## Mobile Action Space
Coordinates use a 0-999 screen scale, where [0,0] is top-left and [999,999] is bottom-right.
Use exactly one mobile_use action each turn.

{"action": "click", "coordinate": [x, y]}
{"action": "long_press", "coordinate": [x, y]}
{"action": "double_click", "coordinate": [x, y]}
{"action": "type", "text": "..."}
{"action": "swipe", "direction": "up|down|left|right", "coordinate": [x, y]}
{"action": "drag", "start_coordinate": [x1, y1], "end_coordinate": [x2, y2]}
{"action": "system_button", "button": "back|home|enter"}
{"action": "open", "text": "app name or package"}
{"action": "wait"}
{"action": "call_user", "text": "question for the user"}
{"action": "answer", "text": "final answer"}
{"action": "status", "goal_status": "complete|infeasible"}

Compatibility aliases are accepted, but prefer the GMA names above:
- ask_user is an alias for call_user.
- terminate with status=success is an alias for status complete.
- terminate with status=fail or failure is an alias for status infeasible.

## Rules
- When you believe the task is fully completed, your next action must be {"action": "status", "goal_status": "complete"}.
- For tasks that ask you to report an exact answer rather than only change the UI, use {"action": "answer", "text": "..."} as the final action.
- Do not continue interacting with the phone after the task is complete.
- Use call_user when the task goal is ambiguous or missing necessary information. Do not guess required user preferences.
- If you need to type text, click the input box first unless it is clearly already focused.
- If the screen is loading or transitioning, use wait.
- Prefer the shortest reliable path.
{app_context}
{user_context}
""".strip()


def _pil_to_data_url(image: Any) -> str:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            stripped = "\n".join(lines[1:-1]).strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    start = stripped.find("{")
    if start < 0:
        raise ValueError("No JSON object found")
    depth = 0
    in_string = False
    escape = False
    for idx in range(start, len(stripped)):
        ch = stripped[idx]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(stripped[start:idx + 1])
    raise ValueError("Unclosed JSON object")


def parse_tagged_text(text: str) -> dict[str, Any]:
    """Parse MAI-UI tagged output into thinking/tool_call fields."""
    if "<think>" in text or "</think>" in text:
        text = text.replace("<think>", "<thinking>").replace("</think>", "</thinking>")

    thinking = None
    thinking_match = re.search(r"<thinking>(.*?)</thinking>", text, re.DOTALL | re.IGNORECASE)
    if thinking_match:
        thinking = thinking_match.group(1).strip().strip('"')

    tool_match = re.search(r"<tool_call>(.*?)</tool_call>", text, re.DOTALL | re.IGNORECASE)
    if tool_match:
        tool_call = _parse_json_object(tool_match.group(1).strip().strip('"'))
    else:
        # Some checkpoints omit tags but still emit the tool call JSON.
        tool_call = _parse_json_object(text)

    return {"thinking": thinking, "tool_call": tool_call}


def _normalize_action_name(action: str | None) -> str:
    if not action:
        return "unknown"
    return action.strip().lower().replace(" ", "_")


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def _coord_to_pixel(coord: Any, width: int, height: int) -> tuple[int, int]:
    if not isinstance(coord, list) or len(coord) not in {2, 4}:
        raise ValueError(f"Invalid coordinate: {coord!r}")
    if len(coord) == 4:
        x1, y1, x2, y2 = coord
        x = (float(x1) + float(x2)) / 2
        y = (float(y1) + float(y2)) / 2
    else:
        x, y = float(coord[0]), float(coord[1])

    if abs(x) <= 1.0 and abs(y) <= 1.0:
        px = int(x * width)
        py = int(y * height)
    elif abs(x) <= SCALE_FACTOR + 1 and abs(y) <= SCALE_FACTOR + 1:
        px = int(x * width / SCALE_FACTOR)
        py = int(y * height / SCALE_FACTOR)
    else:
        # Fallback for models that output absolute pixels despite the prompt.
        px = int(x)
        py = int(y)
    return _clamp(px, 0, width - 1), _clamp(py, 0, height - 1)


def _status_to_goal_status(status: str | None) -> str:
    normalized = (status or "complete").strip().lower()
    if normalized in {"success", "complete", "done", "finished"}:
        return "complete"
    if normalized in {"fail", "failure", "failed", "infeasible", "impossible"}:
        return "infeasible"
    return "complete"


def _mobile_action_to_gma(tool_name: str, args: dict[str, Any], width: int, height: int) -> Action:
    if tool_name != "mobile_use":
        logger.warning(f"Unsupported non-mobile MAI-UI tool call {tool_name!r}; waiting")
        return Action(action_type=ActionType.WAIT)

    action_name = _normalize_action_name(args.get("action") or args.get("action_type"))

    if action_name in {"click", "tap"}:
        x, y = _coord_to_pixel(args.get("coordinate"), width, height)
        return Action(action_type=ActionType.CLICK, x=x, y=y)

    if action_name in {"long_press", "long_tap"}:
        x, y = _coord_to_pixel(args.get("coordinate"), width, height)
        return Action(action_type=ActionType.LONG_PRESS, x=x, y=y)

    if action_name in {"double_click", "double_tap"}:
        x, y = _coord_to_pixel(args.get("coordinate"), width, height)
        return Action(action_type=ActionType.DOUBLE_TAP, x=x, y=y)

    if action_name in {"type", "input_text", "enter_text", "write"}:
        return Action(action_type=ActionType.INPUT_TEXT, text=str(args.get("text", "")))

    if action_name in {"swipe", "scroll"}:
        coord = args.get("coordinate")
        x = y = None
        if coord is not None:
            x, y = _coord_to_pixel(coord, width, height)
        direction = str(args.get("direction", "up")).strip().lower()
        if direction not in {"up", "down", "left", "right"}:
            direction = "up"
        return Action(action_type=ActionType.SCROLL, x=x, y=y, direction=direction)

    if action_name == "drag":
        start = args.get("start_coordinate") or args.get("coordinate")
        end = args.get("end_coordinate") or args.get("coordinate2")
        start_x, start_y = _coord_to_pixel(start, width, height)
        end_x, end_y = _coord_to_pixel(end, width, height)
        return Action(
            action_type=ActionType.DRAG,
            start_x=start_x,
            start_y=start_y,
            end_x=end_x,
            end_y=end_y,
        )

    if action_name == "system_button":
        button = str(args.get("button", "")).strip().lower()
        if button == "back":
            return Action(action_type=ActionType.NAVIGATE_BACK)
        if button == "home":
            return Action(action_type=ActionType.NAVIGATE_HOME)
        if button == "enter":
            return Action(action_type=ActionType.KEYBOARD_ENTER)
        logger.warning(f"Unsupported system_button {button!r}; waiting")
        return Action(action_type=ActionType.WAIT)

    if action_name in {"open", "open_app", "launch"}:
        app_name = args.get("app_name") or args.get("text") or args.get("package") or ""
        return Action(action_type=ActionType.OPEN_APP, app_name=str(app_name))

    if action_name in {"call_user", "ask_user"}:
        return Action(action_type=ActionType.CALL_USER, text=str(args.get("text", "")))

    if action_name == "answer":
        return Action(action_type=ActionType.ANSWER, text=str(args.get("text", "")))

    if action_name in {"status", "terminate", "finish"}:
        goal_status = args.get("goal_status") or args.get("status")
        return Action(action_type=ActionType.STATUS, goal_status=_status_to_goal_status(goal_status))

    if action_name == "wait":
        return Action(action_type=ActionType.WAIT)

    logger.warning(f"Unknown MAI-UI action {action_name!r}; waiting")
    return Action(action_type=ActionType.WAIT)


class MAIUIAgent(BaseAgent, LLMClientMixin):
    """GMA-compatible MAI-UI style agent.

    The model is prompted with MAI-UI's tagged <tool_call> format, while the
    parser accepts both MAI-UI's original ask_user/terminate actions and GMA's
    call_user/status actions.
    """

    def __init__(
        self,
        model_name: str,
        llm_base_url: str,
        api_key: str = "empty",
        runtime_conf: dict[str, Any] | None = None,
        history_n: int = 3,
        **_: Any,
    ):
        self.model_name = model_name
        self.llm_base_url = llm_base_url
        self.api_key = api_key
        self.runtime_conf = {
            "temperature": 0.0,
            "top_p": 1.0,
            "max_tokens": 2048,
        }
        if runtime_conf:
            self.runtime_conf.update(runtime_conf)
        self.history_n = int(os.getenv("HISTORY_N_IMAGES", history_n))
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

    def _render_prompt(self) -> str:
        app_context = ""
        if self._app_context:
            formatted = "\n".join(
                f"- {app_name}: {package}"
                for app_name, package in sorted(self._app_context.items())
            )
            app_context = (
                "\n## Available Apps For This Task\n"
                "Use these exact app names or packages with the open action. Do not invent package names.\n"
                f"{formatted}\n"
            )
        user_context = ""
        if self._user_turns:
            formatted_turns = "\n".join(
                f"- Agent asked: {turn['question']}\n"
                f"  User answered: {turn['response'] or '[no response]'}"
                for turn in self._user_turns[-6:]
            )
            user_context = (
                "\n## User Interaction History\n"
                f"{formatted_turns}\n"
                "Use these answers as authoritative task information.\n"
            )
        return MAI_UI_SYSTEM_PROMPT.replace("{app_context}", app_context).replace("{user_context}", user_context)

    def _build_messages(self, observation: Any) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self._render_prompt()},
            {"role": "user", "content": [{"type": "text", "text": f"Task: {self._goal}"}]},
        ]

        history = list(zip(self._history[-self.history_n :], self._responses[-self.history_n :], strict=False))
        for item, response in history:
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": item["caption"]},
                    {"type": "image_url", "image_url": {"url": item["data_url"]}},
                ],
            })
            messages.append({"role": "assistant", "content": response})

        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": "Current screen. Choose the next single action."},
                {"type": "image_url", "image_url": {"url": _pil_to_data_url(observation.screenshot)}},
            ],
        })
        return messages

    def act(self, observation: Any) -> Action:
        width, height = observation.screenshot.size
        messages = self._build_messages(observation)
        response = self.llm_chat(
            model=self.model_name,
            messages=messages,
            **self.runtime_conf,
        )
        if not response:
            logger.warning("MAI-UI LLM returned no response; waiting")
            return Action(action_type=ActionType.WAIT)

        try:
            parsed = parse_tagged_text(response)
            thinking = parsed.get("thinking")
            tool_call = parsed["tool_call"]
            if not isinstance(tool_call, dict):
                raise ValueError(f"tool_call must be an object, got {type(tool_call).__name__}")
            if "arguments" in tool_call or "name" in tool_call:
                tool_name = tool_call.get("name", "mobile_use")
                args = tool_call.get("arguments", {})
            else:
                # Fallback for checkpoints that output the mobile action JSON directly.
                tool_name = "mobile_use"
                args = tool_call
            if not isinstance(args, dict):
                raise ValueError(f"tool_call.arguments must be an object, got {type(args).__name__}")
            action = _mobile_action_to_gma(tool_name, args, width, height)
            logger.info(f"MAI-UI thinking: {thinking}")
            logger.info(f"MAI-UI action: {tool_name} {args}")
        except Exception as exc:
            logger.warning(f"Failed to parse MAI-UI response, waiting instead: {exc}")
            logger.debug(response)
            action = Action(action_type=ActionType.WAIT)

        self._history.append({
            "caption": f"Previous screen for task: {self._goal}",
            "data_url": _pil_to_data_url(observation.screenshot),
        })
        self._responses.append(response)
        return action

    @property
    def stats(self) -> dict[str, Any]:
        return self.llm_stats()


register_agent("mai_ui", MAIUIAgent)
