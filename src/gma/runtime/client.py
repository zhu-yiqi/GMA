"""HTTP client for communicating with the GMA device proxy server.

``GMAClient`` mirrors the ``AndroidController`` interface so that host-side
code (task setup, evaluation criteria, app helpers) can use it interchangeably.
"""

from __future__ import annotations

import base64
from pathlib import Path
import time
from io import BytesIO

import backoff
import requests
from loguru import logger
from PIL import Image

from gma.assets.models import parse_assets, serialize_asset
from gma.runtime.models import Action, Observation


class DeviceError(Exception):
    """Raised when a device operation fails via the proxy."""


class GMAClient:
    """HTTP client to the GMA device proxy running inside a Docker container.

    Provides the same interface as ``AndroidController`` so host-side code
    (task setup, evaluation, app helpers) works identically whether running
    locally or remotely.
    """

    def __init__(
        self,
        url: str = "http://localhost:8000",
        device: str = "emulator-5554",
        step_wait_time: float = 1.0,
    ):
        self.base_url = url.rstrip("/")
        self.device = device
        self.step_wait_time = step_wait_time
        self.width: int | None = None
        self.height: int | None = None

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def init(self) -> None:
        """Initialize the device controller on the server side."""
        resp = requests.post(f"{self.base_url}/init", json={"device": self.device})
        resp.raise_for_status()
        data = resp.json()
        self.width = data.get("screen_width")
        self.height = data.get("screen_height")
        logger.debug(f"Device initialized: {self.device} ({self.width}x{self.height})")

    def health(self) -> bool:
        """Check if the device proxy and emulator are healthy."""
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=10)
            resp.raise_for_status()
            return resp.json().get("ok", False)
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Screenshots
    # ------------------------------------------------------------------

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def screenshot(self, wait: bool = True) -> Image.Image:
        """Capture the current screen."""
        if wait:
            time.sleep(self.step_wait_time)
        resp = requests.get(
            f"{self.base_url}/screenshot",
            params={"device": self.device},
        )
        resp.raise_for_status()
        b64 = resp.json()["b64_png"]
        img = Image.open(BytesIO(base64.b64decode(b64)))
        img.load()
        return img

    def dump_xml(self) -> str:
        """Dump the current UI hierarchy and return the raw XML."""
        self.shell("uiautomator dump /sdcard/_gma_ui.xml")
        return self.shell("cat /sdcard/_gma_ui.xml")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def step(self, action: Action) -> None:
        """Execute a UI action on the device."""
        resp = requests.post(
            f"{self.base_url}/step",
            json={"device": self.device, "action": action.model_dump()},
        )
        resp.raise_for_status()

    def execute_action(self, action: Action) -> Observation:
        """Execute action and return the resulting observation."""
        self.step(action)
        img = self.screenshot(wait=True)
        return Observation(screenshot=img)

    # ------------------------------------------------------------------
    # Controller-compatible interface
    # ------------------------------------------------------------------

    def tap(self, x: int, y: int) -> None:
        self.step(Action(action_type="click", x=x, y=y))

    def double_tap(self, x: int, y: int) -> None:
        self.step(Action(action_type="double_tap", x=x, y=y))

    def long_press(self, x: int, y: int) -> None:
        self.step(Action(action_type="long_press", x=x, y=y))

    def swipe(self, x: int, y: int, direction: str) -> None:
        self.step(Action(action_type="scroll", x=x, y=y, direction=direction))

    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int) -> None:
        self.step(Action(action_type="drag", start_x=start_x, start_y=start_y, end_x=end_x, end_y=end_y))

    def input_text(self, text: str) -> None:
        self.step(Action(action_type="input_text", text=text))

    def press_enter(self) -> None:
        self.step(Action(action_type="keyboard_enter"))

    def press_home(self) -> None:
        self.step(Action(action_type="navigate_home"))

    def press_back(self) -> None:
        self.step(Action(action_type="navigate_back"))

    def launch_app(self, package_name: str) -> None:
        self.step(Action(action_type="open_app", app_name=package_name))

    def force_stop(self, package_name: str) -> None:
        self.shell(f"am force-stop {package_name}")

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------

    def load_snapshot(self, tag: str, *, log_error: bool = True) -> bool:
        try:
            resp = requests.post(
                f"{self.base_url}/snapshot/load",
                json={"device": self.device, "tag": tag},
            )
            resp.raise_for_status()
            return True
        except Exception as e:
            if log_error:
                logger.error(f"Failed to load snapshot {tag}: {e}")
            return False

    def save_snapshot(self, tag: str) -> str | None:
        try:
            resp = requests.post(
                f"{self.base_url}/snapshot/save",
                json={"device": self.device, "tag": tag},
            )
            resp.raise_for_status()
            return resp.json().get("tag")
        except Exception as e:
            logger.error(f"Failed to save snapshot: {e}")
            return None

    # ------------------------------------------------------------------
    # ADB shell & container exec (used by app helpers)
    # ------------------------------------------------------------------

    def _raise_device_error(self, resp: requests.Response, prefix: str) -> None:
        detail = None
        try:
            payload = resp.json()
            detail = payload.get("detail")
        except Exception:
            detail = resp.text.strip() or None
        if detail:
            raise DeviceError(f"{prefix}: {detail}")
        resp.raise_for_status()

    def shell(self, command: str, timeout: float = 30.0) -> str:
        """Run an ADB shell command on the emulator."""
        resp = requests.post(
            f"{self.base_url}/shell",
            json={"device": self.device, "command": command, "timeout": timeout},
        )
        if not resp.ok:
            self._raise_device_error(resp, "ADB shell failed")
        return resp.json()["output"]

    def exec(self, command: str, timeout: float = 30.0) -> str:
        """Run a bash command inside the container."""
        resp = requests.post(
            f"{self.base_url}/exec",
            json={"command": command, "timeout": timeout},
        )
        if not resp.ok:
            self._raise_device_error(resp, "Container exec failed")
        return resp.json()["output"]

    # ------------------------------------------------------------------
    # Host -> server transport helpers
    # ------------------------------------------------------------------

    def apply_assets_remote(self, assets: list[dict | object]) -> None:
        payload_assets = [
            serialize_asset(a, task_root=Path.cwd())
            for a in parse_assets(assets)
        ]
        elementx_session_assets = [
            asset for asset in payload_assets
            if isinstance(asset, dict) and asset.get("kind") == "elementx_session"
        ]
        non_session_assets = [
            asset for asset in payload_assets
            if not (
                isinstance(asset, dict)
                and asset.get("kind") == "elementx_session"
            )
        ]
        if not elementx_session_assets:
            resp = requests.post(
                f"{self.base_url}/assets/apply",
                json={"device": self.device, "assets": payload_assets},
            )
            if not resp.ok:
                self._raise_device_error(resp, "Asset apply failed")
            return

        if non_session_assets:
            resp = requests.post(
                f"{self.base_url}/assets/apply",
                json={"device": self.device, "assets": non_session_assets},
            )
            if not resp.ok:
                self._raise_device_error(resp, "Asset apply failed")

        payload = {"device": self.device, "assets": elementx_session_assets}
        has_elementx_session = bool(elementx_session_assets)
        max_attempts = 3 if has_elementx_session else 1
        last_response: requests.Response | None = None
        for attempt in range(1, max_attempts + 1):
            resp = requests.post(f"{self.base_url}/assets/apply", json=payload)
            if resp.ok:
                return
            last_response = resp
            if attempt >= max_attempts:
                break
            logger.warning(
                "Asset apply failed for ElementX session batch "
                f"(attempt {attempt}/{max_attempts}): {resp.text[:500]}"
            )
            time.sleep(10 * attempt)
        if last_response is not None:
            self._raise_device_error(last_response, "Asset apply failed")

    def get_terminal_state(self) -> dict[str, object]:
        resp = requests.get(
            f"{self.base_url}/terminal_state",
            params={"device": self.device},
        )
        resp.raise_for_status()
        return resp.json()

    def reset_terminal_state(self) -> None:
        resp = requests.post(
            f"{self.base_url}/terminal_state/reset",
            json={"device": self.device},
        )
        resp.raise_for_status()
