"""ADB controller for direct device interaction.

Used inside the Docker container by the server. On the host side, use
``GMAClient`` which provides the same interface over HTTP.
"""

from __future__ import annotations

import base64
import os
import signal
import shlex
import subprocess
import time
from datetime import datetime
from io import BytesIO

from loguru import logger
from PIL import Image
from gma.apps import resolve_launch_url, resolve_package


class AdbError(Exception):
    """Raised when an ADB command fails."""


def _run_command(command: str, timeout: float) -> subprocess.CompletedProcess[str]:
    """Run a shell command and kill the whole process group on timeout."""
    use_stdin_script = len(command.encode("utf-8")) > 100_000
    if use_stdin_script:
        process = subprocess.Popen(
            ["/bin/bash"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
    else:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
    try:
        stdout, stderr = process.communicate(input=command if use_stdin_script else None, timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
        raise AdbError(f"Command timed out after {timeout}s: {command}") from None
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


def run_adb(command: str, timeout: float = 30.0) -> str:
    """Execute an ADB command and return stdout."""
    result = _run_command(command, timeout)
    if result.returncode != 0:
        raise AdbError(f"Command failed: {command}\nstderr: {result.stderr.strip()}")
    return result.stdout.strip()


def run_shell(command: str, timeout: float = 30.0) -> str:
    """Execute a shell command inside the container and return stdout."""
    result = _run_command(command, timeout)
    if result.returncode != 0:
        raise AdbError(f"Command failed: {command}\nstderr: {result.stderr.strip()}")
    return result.stdout.strip()


class AndroidController:
    """Controls an Android emulator via ADB.

    This class is used directly inside the Docker container by the server.
    """

    def __init__(self, device: str = "emulator-5554"):
        self.device = device
        self.width: int | None = None
        self.height: int | None = None
        self._detect_screen_size()

    # ------------------------------------------------------------------
    # Device info
    # ------------------------------------------------------------------

    def _detect_screen_size(self) -> None:
        try:
            output = run_adb(f"adb -s {self.device} shell wm size", timeout=8)
            resolution = output.split(":")[1].strip()
            w, h = resolution.split("x")
            self.width, self.height = int(w), int(h)
        except Exception as e:
            logger.warning(f"Failed to detect screen size: {e}")

    def check_health(self, retries: int = 3) -> bool:
        """Return True if the device is booted and responsive."""
        for attempt in range(retries):
            try:
                out = run_adb(f"adb -s {self.device} shell getprop sys.boot_completed", timeout=5)
                if out.strip() == "1":
                    return True
            except AdbError:
                pass
            if attempt < retries - 1:
                time.sleep(2)
        return False

    # ------------------------------------------------------------------
    # Screenshots
    # ------------------------------------------------------------------

    def screenshot(self) -> Image.Image:
        """Capture the current screen and return a PIL Image."""
        for attempt in range(3):
            try:
                return self._screenshot_execout()
            except Exception:
                if attempt < 2:
                    time.sleep(0.5)
        return self._screenshot_file()

    def _screenshot_execout(self) -> Image.Image:
        result = subprocess.run(
            f"adb -s {self.device} exec-out screencap -p",
            shell=True, capture_output=True, timeout=10,
        )
        if result.returncode != 0:
            raise AdbError(f"exec-out screencap failed: {result.stderr}")
        img = Image.open(BytesIO(result.stdout))
        img.load()
        return img

    def _screenshot_file(self) -> Image.Image:
        remote = "/sdcard/_gma_screenshot.png"
        local = "/tmp/_gma_screenshot.png"
        run_adb(f"adb -s {self.device} shell screencap -p {remote}")
        try:
            run_adb(f"adb -s {self.device} pull {remote} {local}")
            img = Image.open(local)
            img.load()
            return img
        finally:
            run_adb(f"adb -s {self.device} shell rm -f {remote}")
            if os.path.exists(local):
                os.remove(local)

    # ------------------------------------------------------------------
    # XML / UI hierarchy
    # ------------------------------------------------------------------

    def dump_xml(self, local_path: str | None = None) -> str:
        """Dump the UI hierarchy via uiautomator and return XML content."""
        remote = "/sdcard/_gma_ui.xml"
        local = local_path or "/tmp/_gma_ui.xml"
        for attempt in range(5):
            try:
                run_adb(f"adb -s {self.device} shell uiautomator dump {remote}")
                run_adb(f"adb -s {self.device} pull {remote} {local}")
                with open(local) as f:
                    content = f.read()
                if content:
                    return content
            except AdbError:
                pass
            time.sleep(1)
        raise AdbError("Failed to dump UI XML after 5 attempts")

    # ------------------------------------------------------------------
    # Touch / input actions
    # ------------------------------------------------------------------

    def tap(self, x: int, y: int) -> None:
        run_adb(f"adb -s {self.device} shell input tap {x} {y}")

    def double_tap(self, x: int, y: int) -> None:
        self.tap(x, y)
        time.sleep(0.1)
        self.tap(x, y)

    def long_press(self, x: int, y: int, duration_ms: int = 1000) -> None:
        run_adb(f"adb -s {self.device} shell input swipe {x} {y} {x} {y} {duration_ms}")

    def swipe(self, x: int, y: int, direction: str, duration_ms: int = 400) -> None:
        if self.width is None or self.height is None:
            self._detect_screen_size()
        dist = (self.width or 1080) // 5
        offsets = {
            "up": (0, -dist),
            "down": (0, dist),
            "left": (-dist, 0),
            "right": (dist, 0),
        }
        if direction not in offsets:
            raise ValueError(f"Invalid direction: {direction}")
        dx, dy = offsets[direction]
        run_adb(
            f"adb -s {self.device} shell input swipe {x} {y} {x + dx} {y + dy} {duration_ms}"
        )

    def drag(
        self, start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 400
    ) -> None:
        run_adb(
            f"adb -s {self.device} shell input swipe "
            f"{start_x} {start_y} {end_x} {end_y} {duration_ms}"
        )

    def input_text(self, text: str) -> None:
        """Type text using AdbIME (supports Unicode via base64 broadcast)."""
        encoded = str(base64.b64encode(text.encode("utf-8")))[1:]
        run_adb(
            f"adb -s {self.device} shell am broadcast "
            f"-a ADB_INPUT_B64 --es msg {encoded}"
        )

    def press_key(self, keycode: str) -> None:
        run_adb(f"adb -s {self.device} shell input keyevent {keycode}")

    def press_enter(self) -> None:
        self.press_key("KEYCODE_ENTER")

    def press_back(self) -> None:
        self.press_key("KEYCODE_BACK")

    def press_home(self) -> None:
        self.press_key("KEYCODE_HOME")

    def app_switch(self) -> None:
        self.press_key("KEYCODE_APP_SWITCH")

    # ------------------------------------------------------------------
    # App launch
    # ------------------------------------------------------------------

    def launch_app(self, package_name: str) -> None:
        launch_url = resolve_launch_url(package_name)
        if launch_url:
            run_adb(
                f"adb -s {self.device} shell am start "
                f"-a android.intent.action.VIEW -d {shlex.quote(launch_url)} com.android.chrome"
            )
            return
        package_name = resolve_package(package_name)
        run_adb(
            f"adb -s {self.device} shell monkey "
            f"-p {package_name} -c android.intent.category.LAUNCHER 1"
        )

    def force_stop(self, package_name: str) -> None:
        run_adb(f"adb -s {self.device} shell am force-stop {package_name}")

    # ------------------------------------------------------------------
    # SMS
    # ------------------------------------------------------------------

    def inject_sms(self, sender: str, message: str) -> None:
        run_adb(
            f"adb -s {self.device} emu sms send "
            f"{shlex.quote(sender)} {shlex.quote(message)}"
        )

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------

    def load_snapshot(self, tag: str) -> bool:
        try:
            out = run_adb(f"adb -s {self.device} emu avd snapshot load {tag}")
            if "OK" in out:
                time.sleep(3)
                return True
            logger.error(f"Snapshot load returned: {out}")
            return False
        except AdbError as e:
            logger.error(f"Failed to load snapshot {tag}: {e}")
            return False

    def save_snapshot(self, tag: str | None = None) -> str | None:
        if tag is None:
            fmt = "%Y%m%d_%H%M%S"
            tag = f"snapshot_{datetime.now().strftime(fmt)}"
        try:
            out = run_adb(f"adb -s {self.device} emu avd snapshot save {tag}")
            return tag if "OK" in out else None
        except AdbError as e:
            logger.error(f"Failed to save snapshot: {e}")
            return None

    def delete_snapshot(self, tag: str) -> bool:
        try:
            out = run_adb(f"adb -s {self.device} emu avd snapshot delete {tag}")
            return "OK" in out
        except AdbError as e:
            logger.error(f"Failed to delete snapshot {tag}: {e}")
            return False

    def list_snapshots(self) -> list[str]:
        try:
            out = run_adb(f"adb -s {self.device} emu avd snapshot list")
            return [line.strip() for line in out.splitlines() if line.strip() and "OK" not in line]
        except AdbError:
            return []

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def push_file(self, local_path: str, remote_path: str) -> None:
        run_adb(f"adb -s {self.device} push {local_path} {remote_path}")

    def pull_file(self, remote_path: str, local_path: str) -> None:
        run_adb(f"adb -s {self.device} pull {remote_path} {local_path}")

    def remove_file(self, remote_path: str) -> None:
        run_adb(f"adb -s {self.device} shell rm -f {remote_path}")

    # ------------------------------------------------------------------
    # Generic shell commands
    # ------------------------------------------------------------------

    def shell(self, command: str) -> str:
        """Run an ADB shell command and return output."""
        return run_adb(f"adb -s {self.device} shell {command}")

    def exec(self, command: str, timeout: float = 30.0) -> str:
        """Run a bash command inside the container (not on the Android device)."""
        return run_shell(command, timeout=timeout)
