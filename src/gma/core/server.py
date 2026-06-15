"""FastAPI server — runs inside the Docker container as a device proxy.

This server knows nothing about tasks. It exposes low-level device operations
(screenshot, UI actions, ADB shell, container shell, snapshots) so that the
host-side runner can orchestrate task lifecycle remotely.
"""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass, field
from io import BytesIO

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel

from gma.assets.apply import apply_assets
from gma.assets.models import Asset
from gma.runtime.controller import AndroidController, AdbError
from gma.runtime.models import Action, ActionType


# ---------------------------------------------------------------------------
# Server state
# ---------------------------------------------------------------------------


@dataclass
class ServerState:
    controllers: dict[str, AndroidController] = field(default_factory=dict)
    terminal_state: dict[str, dict[str, str | float | None]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class InitRequest(BaseModel):
    device: str = "emulator-5554"


class StepRequest(BaseModel):
    device: str = "emulator-5554"
    action: Action


class SnapshotRequest(BaseModel):
    device: str = "emulator-5554"
    tag: str


class ShellRequest(BaseModel):
    device: str = "emulator-5554"
    command: str
    timeout: float = 30.0


class ExecRequest(BaseModel):
    command: str
    timeout: float = 30.0


class AssetApplyRequest(BaseModel):
    device: str = "emulator-5554"
    assets: list[Asset]


class DeviceRequest(BaseModel):
    device: str = "emulator-5554"


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="GMA Device Proxy", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    app.state.server = ServerState()
    logger.info("GMA device proxy started")


def _get_controller(device: str) -> AndroidController:
    state: ServerState = app.state.server
    if device not in state.controllers:
        logger.info(f"Initializing controller for {device}")
        state.controllers[device] = AndroidController(device=device)
    ctrl = state.controllers[device]
    if not ctrl.check_health(retries=3):
        logger.warning(f"Device {device} unhealthy, reinitializing controller")
        ctrl = AndroidController(device=device)
        state.controllers[device] = ctrl
        if not ctrl.check_health(retries=3):
            raise HTTPException(status_code=503, detail=f"Device {device} is not healthy")
    return ctrl


def _get_terminal_state(device: str) -> dict[str, str | float | None]:
    state: ServerState = app.state.server
    if device not in state.terminal_state:
        state.terminal_state[device] = {
            "answer_text": None,
            "goal_status": None,
            "last_user_question": None,
            "updated_at": None,
        }
    return state.terminal_state[device]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
def health():
    state: ServerState = app.state.server
    statuses = {}
    for device_id, ctrl in state.controllers.items():
        statuses[device_id] = ctrl.check_health(retries=2)
    return {"ok": all(statuses.values()) if statuses else True, "devices": statuses}


@app.post("/init")
def init_device(req: InitRequest):
    ctrl = _get_controller(req.device)
    return {
        "device": req.device,
        "screen_width": ctrl.width,
        "screen_height": ctrl.height,
    }


@app.get("/screenshot")
def screenshot(device: str = "emulator-5554"):
    ctrl = _get_controller(device)
    try:
        img = ctrl.screenshot()
        buf = BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        return {"b64_png": b64, "width": img.width, "height": img.height}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Screenshot failed: {e}")


@app.post("/step")
def step(req: StepRequest):
    ctrl = _get_controller(req.device)
    action = req.action
    try:
        match action.action_type:
            case ActionType.CLICK:
                ctrl.tap(action.x, action.y)
            case ActionType.DOUBLE_TAP:
                ctrl.double_tap(action.x, action.y)
            case ActionType.LONG_PRESS:
                ctrl.long_press(action.x, action.y)
            case ActionType.SCROLL:
                x = action.x if action.x is not None else (ctrl.width or 540) // 2
                y = action.y if action.y is not None else (ctrl.height or 1200) // 2
                ctrl.swipe(x, y, action.direction)
            case ActionType.INPUT_TEXT:
                ctrl.input_text(action.text)
            case ActionType.KEYBOARD_ENTER:
                ctrl.press_enter()
            case ActionType.NAVIGATE_HOME:
                ctrl.press_home()
            case ActionType.NAVIGATE_BACK:
                ctrl.press_back()
            case ActionType.OPEN_APP:
                ctrl.launch_app(action.app_name)
            case ActionType.DRAG:
                ctrl.drag(action.start_x, action.start_y, action.end_x, action.end_y)
            case ActionType.WAIT:
                time.sleep(1)
            case ActionType.CALL_USER:
                terminal = _get_terminal_state(req.device)
                terminal["last_user_question"] = action.text
                terminal["updated_at"] = time.time()
            case ActionType.ANSWER:
                terminal = _get_terminal_state(req.device)
                terminal["answer_text"] = action.text
                terminal["goal_status"] = None
                terminal["updated_at"] = time.time()
            case ActionType.STATUS:
                terminal = _get_terminal_state(req.device)
                terminal["goal_status"] = action.goal_status
                terminal["updated_at"] = time.time()
            case _:
                raise HTTPException(status_code=400, detail=f"Unknown action: {action.action_type}")
        return {"status": "ok", "action_type": action.action_type}
    except AdbError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/snapshot/load")
def snapshot_load(req: SnapshotRequest):
    ctrl = _get_controller(req.device)
    ok = ctrl.load_snapshot(req.tag)
    if not ok:
        raise HTTPException(status_code=500, detail=f"Failed to load snapshot: {req.tag}")
    return {"status": "ok", "tag": req.tag}


@app.post("/snapshot/save")
def snapshot_save(req: SnapshotRequest):
    ctrl = _get_controller(req.device)
    tag = ctrl.save_snapshot(req.tag)
    if tag is None:
        raise HTTPException(status_code=500, detail="Failed to save snapshot")
    return {"status": "ok", "tag": tag}


@app.post("/shell")
def adb_shell(req: ShellRequest):
    ctrl = _get_controller(req.device)
    try:
        output = ctrl.shell(req.command)
        return {"output": output}
    except AdbError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/exec")
def container_exec(req: ExecRequest):
    from gma.runtime.controller import run_shell
    try:
        output = run_shell(req.command, timeout=req.timeout)
        return {"output": output}
    except AdbError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/assets/apply")
def asset_apply(req: AssetApplyRequest):
    ctrl = _get_controller(req.device)
    try:
        apply_assets(ctrl, list(req.assets))
        return {"status": "ok", "count": len(req.assets)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Asset apply failed: {e}")


@app.get("/terminal_state")
def terminal_state(device: str = "emulator-5554"):
    return _get_terminal_state(device)


@app.post("/terminal_state/reset")
def terminal_state_reset(req: DeviceRequest):
    state = _get_terminal_state(req.device)
    state["answer_text"] = None
    state["goal_status"] = None
    state["last_user_question"] = None
    state["updated_at"] = None
    return {"status": "ok"}


def start_server(host: str = "0.0.0.0", port: int = 8000):
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    start_server()
