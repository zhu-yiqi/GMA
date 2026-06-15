"""Docker container management for GMA environments."""

from __future__ import annotations

import json
import os
import re
import shlex
import socket
import subprocess
import time
import urllib.error
import urllib.request

from loguru import logger

DEFAULT_IMAGE = "gma:latest"
DEFAULT_PREFIX = "gma_env"
BASE_BACKEND_PORT = 8100
# Browser noVNC endpoint. The raw VNC server remains inside the container on 5900.
BASE_VNC_PORT = 5920
BASE_ADB_PORT = 5570


def _docker(cmd: str, timeout: float = 60.0) -> str:
    """Run a docker CLI command and return stdout."""
    result = subprocess.run(
        f"docker {cmd}",
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"docker command failed: docker {cmd}\n{result.stderr.strip()}")
    return result.stdout.strip()


# ------------------------------------------------------------------
# Discovery
# ------------------------------------------------------------------


def discover_containers(
    image_filter: str = DEFAULT_IMAGE,
    prefix: str = DEFAULT_PREFIX,
) -> list[dict]:
    """Find running GMA containers and return their connection info.

    Returns a list of dicts with keys: name, backend_url, container_id.
    """
    fmt = '{{.ID}}\\t{{.Names}}\\t{{.Image}}\\t{{.Ports}}'
    try:
        raw = _docker(f'ps --format "{fmt}" --filter name={prefix}')
    except RuntimeError:
        return []

    containers = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        cid, name, image, ports = parts[0], parts[1], parts[2], parts[3]
        backend_port = _extract_port(ports, 8000)
        vnc_port = _extract_port(ports, 5800)
        raw_vnc_port = _extract_port(ports, 5900)
        if backend_port:
            containers.append(
                {
                    "name": name,
                    "container_id": cid,
                    "image": image,
                    "backend_url": f"http://localhost:{backend_port}",
                    "backend_port": backend_port,
                    "vnc_port": vnc_port,
                    "raw_vnc_port": raw_vnc_port,
                }
            )
    return containers


def discover_backend_urls(
    image_filter: str = DEFAULT_IMAGE,
    prefix: str = DEFAULT_PREFIX,
) -> tuple[list[str], list[str]]:
    """Return (urls, names) for all running GMA containers."""
    containers = discover_containers(image_filter, prefix)
    urls = [c["backend_url"] for c in containers]
    names = [c["name"] for c in containers]
    return urls, names


def _extract_port(ports_str: str, container_port: int) -> int | None:
    """Extract the host port mapped to a given container port from docker ps output."""
    for mapping in ports_str.split(","):
        mapping = mapping.strip()
        if f"->{container_port}" in mapping:
            try:
                host_part = mapping.split("->")[0]
                return int(host_part.split(":")[-1])
            except (ValueError, IndexError):
                continue
    return None


def _host_port_available(port: int) -> bool:
    """Return whether a TCP host port can be bound for Docker publishing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("0.0.0.0", port))
        except OSError:
            return False
    return True


def _index_ports_available(idx: int, enable_vnc: bool = True) -> bool:
    ports = [BASE_BACKEND_PORT + idx, BASE_ADB_PORT + idx]
    if enable_vnc:
        ports.append(BASE_VNC_PORT + idx)
    return all(_host_port_available(port) for port in ports)


def _next_container_indices(prefix: str, count: int, enable_vnc: bool = True) -> list[int]:
    """Return numeric suffixes whose container names and host ports are free."""
    raw = _docker('ps -a --format "{{.Names}}"', timeout=15)
    used: set[int] = set()
    pattern = re.compile(rf"^{re.escape(prefix)}_(\d+)$")
    for name in raw.splitlines():
        match = pattern.match(name.strip())
        if match:
            used.add(int(match.group(1)))

    indices: list[int] = []
    candidate = 0
    while len(indices) < count:
        if candidate not in used and _index_ports_available(candidate, enable_vnc=enable_vnc):
            indices.append(candidate)
        candidate += 1
    return indices


def _wait_for_container_ready(
    name: str,
    backend_port: int,
    timeout: float = 300.0,
    poll_interval: float = 2.0,
) -> None:
    """Wait until the container backend is reachable, or raise on failure."""
    deadline = time.time() + timeout
    url = f"http://127.0.0.1:{backend_port}/health"
    last_status = "unknown"
    while time.time() < deadline:
        try:
            status = _docker(
                f'inspect -f "{{{{.State.Status}}}} {{{{if .State.Health}}}}{{{{.State.Health.Status}}}}{{{{else}}}}none{{{{end}}}}" {name}',
                timeout=15,
            ).strip()
            parts = status.split(maxsplit=1)
            state = parts[0] if parts else "unknown"
            health = parts[1] if len(parts) > 1 else "none"
            last_status = status
            if state in {"exited", "dead"}:
                raise RuntimeError(f"Container {name} is not running: {status}")
            if health == "unhealthy":
                raise RuntimeError(f"Container {name} became unhealthy")
        except RuntimeError as e:
            last_status = str(e)

        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                if resp.status == 200:
                    payload = json.loads(resp.read().decode() or "{}")
                    if payload.get("ok", True):
                        return
        except Exception:
            pass

        time.sleep(poll_interval)
    raise RuntimeError(
        f"Timed out waiting for container {name} backend to become ready at {url} (last status: {last_status})"
    )


def _should_bootstrap_ready_image(image: str) -> bool:
    """Ready images should be immediately usable after `gma env up` returns."""
    repo_tag = image.rsplit("/", 1)[-1].lower()
    if ":" not in repo_tag:
        return False
    _, tag = repo_tag.rsplit(":", 1)
    return "ready" in tag


def _verify_ready_webapps(name: str) -> None:
    checks = (
        "http://localhost:8040",
        "http://localhost:8042",
        "http://localhost:8030",
        "http://localhost:8050/meituan/",
        "http://localhost:8070/hmdp/",
        "http://localhost:8071/shop-type/list",
    )
    probe = " ".join(f'"{url}"' for url in checks)
    script = f"set -eu; for url in {probe}; do curl -fsS --max-time 8 \"$url\" >/dev/null; done"
    _docker(f"exec {name} sh -lc {shlex.quote(script)}", timeout=90)


def _bootstrap_ready_container(name: str, backend_port: int, image: str) -> None:
    """Restore runtime services and launcher shortcuts for warmed ready images."""
    if not _should_bootstrap_ready_image(image):
        return

    from gma.runtime.client import GMAClient
    from gma.tasks.base import (
        _ensure_ready_state_launcher_icons,
        ensure_ready_state_apps,
        load_snapshot_state_status,
        reset_backend_state,
    )

    url = f"http://localhost:{backend_port}"
    logger.info(f"Bootstrapping ready container {name} ({url})")
    client = GMAClient(url=url)
    client.init()

    status = load_snapshot_state_status(client, snapshot="gma_ready_state")
    if not status.get("ok"):
        raise RuntimeError(f"Failed to load gma_ready_state in {name}: {status}")

    if not reset_backend_state(client):
        raise RuntimeError(f"Failed to restore backend services in {name}")

    if not ensure_ready_state_apps(client, snapshot="gma_ready_state", bootstrap_apps=False):
        raise RuntimeError(f"Failed to repair ready-state app sessions in {name}")

    saved = client.save_snapshot("gma_ready_state")
    if not saved:
        raise RuntimeError(f"Failed to save repaired gma_ready_state in {name}")

    _ensure_ready_state_launcher_icons(client)
    client.press_home()
    _verify_ready_webapps(name)
    logger.info(f"Ready container {name} bootstrap complete")



# ------------------------------------------------------------------
# Lifecycle
# ------------------------------------------------------------------


def launch_container(
    name: str,
    image: str = DEFAULT_IMAGE,
    backend_port: int = 8000,
    vnc_port: int = 5900,
    adb_port: int = 5556,
    privileged: bool = True,
    enable_vnc: bool = True,
    extra_args: str = "",
) -> str:
    """Launch a single GMA container. Returns the container ID."""
    priv_flag = "--privileged" if privileged else ""
    vnc_env = f"-e ENABLE_VNC={'true' if enable_vnc else 'false'}"
    vnc_mapping = f"-p {vnc_port}:5800" if enable_vnc else ""
    data_mount = ""
    if os.path.isdir("/data/zhuyiqi"):
        data_mount = "-v /data/zhuyiqi:/data/zhuyiqi:ro"
    cmd = (
        f"run -d --name {name} "
        f"-p {backend_port}:8000 "
        f"{vnc_mapping} "
        f"-p {adb_port}:5556 "
        f"{vnc_env} {priv_flag} {data_mount} {extra_args} {image}"
    )
    cid = _docker(cmd)
    logger.info(
        f"Launched container {name} (id={cid[:12]}, backend={backend_port}, "
        f"vnc={vnc_port if enable_vnc else 'disabled'})"
    )
    _wait_for_container_ready(name, backend_port)
    _bootstrap_ready_container(name, backend_port, image)
    logger.info(f"Container {name} is healthy")
    return cid


def launch_containers(
    count: int,
    image: str = DEFAULT_IMAGE,
    prefix: str = DEFAULT_PREFIX,
    launch_interval: float = 15.0,
    enable_vnc: bool = True,
) -> list[dict]:
    """Launch multiple GMA containers with sequential port assignments."""
    results = []
    indices = _next_container_indices(prefix, count, enable_vnc=enable_vnc)
    for pos, idx in enumerate(indices):
        name = f"{prefix}_{idx}"
        backend_port = BASE_BACKEND_PORT + idx
        vnc_port = BASE_VNC_PORT + idx
        adb_port = BASE_ADB_PORT + idx
        try:
            cid = launch_container(
                name=name,
                image=image,
                backend_port=backend_port,
                vnc_port=vnc_port,
                adb_port=adb_port,
                enable_vnc=enable_vnc,
            )
            result = {
                "name": name,
                "container_id": cid,
                "backend_url": f"http://localhost:{backend_port}",
                "backend_port": backend_port,
                "vnc_port": vnc_port if enable_vnc else None,
            }
            if enable_vnc:
                result["vnc_url"] = f"http://localhost:{vnc_port}/vnc.html"
            results.append(result)
        except RuntimeError as e:
            logger.error(f"Failed to launch container {name}: {e}")
        if pos < count - 1:
            time.sleep(launch_interval)
    return results


def stop_container(name: str) -> None:
    """Stop and remove a container by name."""
    try:
        _docker(f"stop {name}", timeout=30)
    except RuntimeError:
        pass
    try:
        _docker(f"rm -f {name}", timeout=30)
    except RuntimeError:
        pass
    logger.info(f"Stopped container {name}")


def stop_all_containers(prefix: str = DEFAULT_PREFIX) -> None:
    """Stop and remove all GMA containers."""
    containers = discover_containers(prefix=prefix)
    for c in containers:
        stop_container(c["name"])


def exec_in_container(name: str, command: str, timeout: float = 60.0) -> str:
    """Execute a command inside a running container."""
    return _docker(f"exec {name} bash -c {json.dumps(command)}", timeout=timeout)
