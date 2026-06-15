from __future__ import annotations

import base64
import shlex
from typing import TYPE_CHECKING
from xml.sax.saxutils import escape

if TYPE_CHECKING:
    from gma.runtime.controller import AndroidController


def run_bash(client: AndroidController, script: str, timeout: float = 120.0) -> str:
    payload = base64.b64encode(script.encode("utf-8")).decode("ascii")
    command = (
        "cat <<__GMA_APP_B64__ | base64 -d > /tmp/gma_app.sh\n"
        f"{payload}\n"
        "__GMA_APP_B64__\n"
        "bash /tmp/gma_app.sh"
    )
    return client.exec(command, timeout=timeout)


def _login_prefs_xml(extras: dict[str, str | int | None]) -> str | None:
    values = [(key, str(value)) for key, value in extras.items() if value is not None]
    if not values:
        return None
    lines = ["<?xml version='1.0' encoding='utf-8' standalone='yes' ?>", "<map>"]
    for key, value in values:
        lines.append(f'    <string name="{escape(key)}">{escape(value)}</string>')
    lines.append("</map>")
    return "\n".join(lines) + "\n"


def launch_webapp_with_login_extras(
    client: AndroidController,
    package: str,
    *,
    timeout: float = 30.0,
    **extras: str | int | None,
) -> str:
    """Launch a GMA WebView wrapper and persist account extras before startup."""
    device = getattr(client, "device", "emulator-5554")
    args = [
        "adb",
        "-s",
        str(device),
        "shell",
        "am",
        "start",
        "-n",
        f"{package}/.MainActivity",
    ]
    for key, value in extras.items():
        if value is None:
            continue
        args.extend(["--es", f"gma_{key}", str(value)])
    start_command = " ".join(shlex.quote(arg) for arg in args)
    device_arg = shlex.quote(str(device))
    package_arg = shlex.quote(package)
    prefs_xml = _login_prefs_xml(extras)
    if prefs_xml is None:
        return run_bash(client, start_command, timeout=timeout)

    prefs_payload = base64.b64encode(prefs_xml.encode("utf-8")).decode("ascii")
    package_dir = shlex.quote(f"/data/user/0/{package}")
    prefs_dir = shlex.quote(f"/data/user/0/{package}/shared_prefs")
    prefs_dest = shlex.quote(f"/data/user/0/{package}/shared_prefs/gma_login.xml")
    tmp_dest = shlex.quote("/data/local/tmp/gma_login.xml")
    script = f"""
set -euo pipefail
adb -s {device_arg} shell am force-stop {package_arg} >/dev/null 2>&1 || true
cat <<'__GMA_PREF_B64__' | base64 -d >/tmp/gma_login.xml
{prefs_payload}
__GMA_PREF_B64__
adb -s {device_arg} root >/dev/null 2>&1 || true
adb -s {device_arg} wait-for-device >/dev/null 2>&1 || true
adb -s {device_arg} push /tmp/gma_login.xml {tmp_dest} >/dev/null
adb -s {device_arg} shell "if [ -d {package_dir} ]; then mkdir -p {prefs_dir}; owner=\\$(stat -c '%u:%g' {package_dir} 2>/dev/null || echo ''); cp {tmp_dest} {prefs_dest}; if [ -n \\"\\$owner\\" ]; then chown \\"\\$owner\\" {prefs_dest}; fi; chmod 600 {prefs_dest}; fi"
{start_command}
"""
    return run_bash(client, script, timeout=timeout)
