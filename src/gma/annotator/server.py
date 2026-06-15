"""Host-side web annotation service for manual GMA task verification."""

from __future__ import annotations

import asyncio
import base64
import contextlib
import inspect
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from dataclasses import dataclass, field
from io import BytesIO
from threading import RLock, Thread
from typing import Any

import uvicorn
import websockets
from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from pydantic import BaseModel

from gma.agents.user_simulator import UserSimulator
from gma.core.config import load_config, resolve_agent_config
from gma.core.task_runtime import load_task, resolve_client
from gma.evaluation.result import EvalResult
from gma.runtime.docker import BASE_BACKEND_PORT, BASE_VNC_PORT, discover_containers
from gma.runtime.models import Action
from gma.tasks.base import BaseTask
from gma.tasks.registry import TaskRegistry


VISIBLE_ENV_IDS = set(range(19, 24))


class StartSessionRequest(BaseModel):
    task_name: str
    url: str | None = None
    device: str = "emulator-5554"
    force: bool = False


class ActionRequest(BaseModel):
    action: Action


class AskUserRequest(BaseModel):
    question: str


class PasteTextRequest(BaseModel):
    text: str


@dataclass
class AnnotationSession:
    id: str
    task: BaseTask
    url: str
    device: str
    client: Any
    container_name: str | None
    user_simulator: UserSimulator | None = None
    user_turns: list[dict[str, Any]] = field(default_factory=list)
    vnc_port: int | None = None
    started_at: float = field(default_factory=time.time)
    last_result: EvalResult | None = None
    last_eval_at: float | None = None


@dataclass
class AnnotatorState:
    default_url: str | None = None
    default_device: str = "emulator-5554"
    task_dirs: tuple[str, ...] = ()
    token: str | None = None
    sessions: dict[str, AnnotationSession] = field(default_factory=dict)
    starting: set[tuple[str | None, str]] = field(default_factory=set)
    start_errors: dict[tuple[str | None, str], str] = field(default_factory=dict)
    lock: RLock = field(default_factory=RLock)


def create_app(
    *,
    default_url: str | None = None,
    default_device: str = "emulator-5554",
    task_dirs: list[str] | None = None,
    token: str | None = None,
) -> FastAPI:
    resolved_task_dirs = tuple(task_dirs if task_dirs is not None else _default_task_dirs())

    app = FastAPI(title="GMA Annotator", version="0.3.0")
    app.state.annotator = AnnotatorState(
        default_url=default_url,
        default_device=default_device,
        task_dirs=resolved_task_dirs,
        token=(token or None),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def api_token_middleware(request: Request, call_next):
        state: AnnotatorState = request.app.state.annotator
        protected = request.url.path.startswith("/api") or request.url.path.startswith("/vnc")
        if state.token and protected and _supplied_token(request) != state.token:
            if request.url.path.startswith("/vnc"):
                return Response("Unauthorized", status_code=401)
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        return await call_next(request)

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request):
        state: AnnotatorState = request.app.state.annotator
        response = HTMLResponse(INDEX_HTML)
        if state.token and request.query_params.get("token") == state.token:
            response.set_cookie("gma_token", state.token, httponly=False, samesite="lax")
        return response

    @app.get("/api/health")
    def health():
        state: AnnotatorState = app.state.annotator
        with state.lock:
            active_sessions = len(state.sessions)
            starting_sessions = len(state.starting)
            start_errors = [
                {"url": key[0], "device": key[1], "detail": detail}
                for key, detail in state.start_errors.items()
            ]
        return {
            "ok": True,
            "active_sessions": active_sessions,
            "starting_sessions": starting_sessions,
            "start_errors": start_errors,
            "default_url": state.default_url,
            "default_device": state.default_device,
            "vnc_proxy": True,
        }

    @app.get("/api/environments")
    def environments(request: Request):
        state: AnnotatorState = app.state.annotator
        containers = sorted(
            _visible_containers(),
            key=lambda item: (
                item.get("backend_url", "").rstrip("/") != (state.default_url or "").rstrip("/"),
                item.get("backend_port") or 0,
                item.get("name") or "",
            ),
        )
        items = [_environment_payload(container, request=request) for container in containers]
        if (
            state.default_url
            and _backend_url_is_visible(state.default_url)
            and all(item["url"] != state.default_url for item in items)
        ):
            items.insert(
                0,
                _environment_payload(
                    {
                        "name": "configured",
                        "backend_url": state.default_url,
                        "backend_port": _url_port(state.default_url),
                        "image": None,
                    },
                    request=request,
                ),
            )
        return {
            "environments": items,
            "default_url": state.default_url,
            "default_device": state.default_device,
        }

    @app.get("/api/tasks")
    def tasks():
        state: AnnotatorState = app.state.annotator
        registry = TaskRegistry(*state.task_dirs, include_builtin=not state.task_dirs)
        return {
            "tasks": sorted(registry.list_tasks(), key=lambda item: item["name"]),
            "task_dirs": list(state.task_dirs),
        }

    @app.get("/api/task/{task_name}/code")
    def task_code(task_name: str):
        state: AnnotatorState = app.state.annotator
        registry = TaskRegistry(*state.task_dirs, include_builtin=not state.task_dirs)
        if not registry.has(task_name):
            raise HTTPException(status_code=404, detail=f"Task not found: {task_name}")
        task = registry.get(task_name)
        source_path = inspect.getsourcefile(task.__class__)
        if not source_path:
            raise HTTPException(status_code=404, detail=f"Source file not found for {task_name}")
        path = Path(source_path).resolve()
        try:
            code = path.read_text(encoding="utf-8")
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to read task source: {exc}") from exc
        return {
            "name": task_name,
            "path": _display_path(path),
            "code": code,
        }

    @app.get("/api/sessions")
    def sessions(request: Request):
        state: AnnotatorState = app.state.annotator
        with state.lock:
            payloads = [_session_payload(session, request=request) for session in state.sessions.values()]
        return {"sessions": payloads}

    @app.post("/api/session/start")
    def start_session(req: StartSessionRequest, request: Request):
        state: AnnotatorState = app.state.annotator
        url = req.url or state.default_url
        device = req.device or state.default_device
        if url and not _backend_url_is_visible(url):
            raise HTTPException(status_code=403, detail="This annotator only exposes gma_env_19 through gma_env_23")
        start_key = _session_key(url=url, device=device)
        existing: AnnotationSession | None = None

        with state.lock:
            existing = _find_session(state, url=url, device=device)
            if existing and not req.force:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"{existing.container_name or existing.url} already has an active "
                        f"session for {existing.task.name}"
                    ),
                )
            if start_key in state.starting:
                raise HTTPException(
                    status_code=409,
                    detail="A session is already starting for " + (url or "the configured environment"),
                )
            state.starting.add(start_key)
            state.start_errors.pop(start_key, None)
            if existing:
                state.sessions.pop(existing.id, None)

        def worker() -> None:
            try:
                if existing:
                    _finalize_session(existing)

                context = resolve_client(url=url, device=device)
                if context is None:
                    raise RuntimeError("No running GMA containers found")

                try:
                    task = load_task(
                        req.task_name,
                        extra_task_dirs=list(state.task_dirs),
                        include_builtin=not state.task_dirs,
                    )
                except KeyError as exc:
                    raise RuntimeError(str(exc)) from exc

                initialized = task.initialize(context.client)
                if not initialized:
                    raise RuntimeError(f"Task initialization failed for {task.name}")

                session = AnnotationSession(
                    id=uuid.uuid4().hex,
                    task=task,
                    url=context.url,
                    device=context.device,
                    client=context.client,
                    container_name=context.container_name,
                    user_simulator=UserSimulator.from_task(task, **_user_simulator_kwargs()),
                    vnc_port=_vnc_port_for_backend_url(context.url),
                )
                session.last_result = _evaluate_session(session)
                session.last_eval_at = time.time()

                superseded: AnnotationSession | None = None
                with state.lock:
                    current = _find_session(state, url=session.url, device=session.device)
                    if current:
                        superseded = current
                        state.sessions.pop(current.id, None)
                    state.sessions[session.id] = session
                    state.start_errors.pop(start_key, None)

                if superseded:
                    _finalize_session(superseded)
            except Exception as exc:
                with state.lock:
                    state.start_errors[start_key] = f"{type(exc).__name__}: {exc}"
            finally:
                with state.lock:
                    state.starting.discard(start_key)

        Thread(target=worker, daemon=True).start()
        return JSONResponse(
            status_code=202,
            content={
                "starting": True,
                "url": url,
                "device": device,
                "task_name": req.task_name,
            },
        )

    @app.get("/api/session/{session_id}")
    def get_session(session_id: str, request: Request):
        state: AnnotatorState = app.state.annotator
        return _session_payload(_session_or_404(state, session_id), request=request)

    @app.get("/api/session/{session_id}/screenshot")
    def screenshot(session_id: str):
        state: AnnotatorState = app.state.annotator
        session = _session_or_404(state, session_id)
        try:
            img = session.client.screenshot(wait=False)
            buf = BytesIO()
            img.save(buf, format="PNG")
            return {
                "b64_png": base64.b64encode(buf.getvalue()).decode("ascii"),
                "width": img.width,
                "height": img.height,
                "ts": time.time(),
            }
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Screenshot failed: {exc}") from exc

    @app.get("/api/session/{session_id}/screenshot.png")
    def screenshot_png(session_id: str):
        state: AnnotatorState = app.state.annotator
        session = _session_or_404(state, session_id)
        try:
            img = session.client.screenshot(wait=False)
            buf = BytesIO()
            img.save(buf, format="PNG")
            return Response(
                content=buf.getvalue(),
                media_type="image/png",
                headers={"Cache-Control": "no-store"},
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Screenshot failed: {exc}") from exc

    @app.post("/api/session/{session_id}/action")
    def action(session_id: str, req: ActionRequest):
        state: AnnotatorState = app.state.annotator
        session = _session_or_404(state, session_id)
        try:
            session.client.step(req.action)
            return {"status": "ok", "action_type": req.action.action_type}
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Action failed: {exc}") from exc

    @app.post("/api/session/{session_id}/paste")
    def paste_text(session_id: str, req: PasteTextRequest):
        state: AnnotatorState = app.state.annotator
        session = _session_or_404(state, session_id)
        if req.text == "":
            raise HTTPException(status_code=400, detail="Paste text cannot be empty")
        try:
            session.client.input_text(req.text)
            return {"status": "ok", "chars": len(req.text)}
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Paste failed: {exc}") from exc

    @app.post("/api/session/{session_id}/ask_user")
    def ask_user(session_id: str, req: AskUserRequest):
        state: AnnotatorState = app.state.annotator
        session = _session_or_404(state, session_id)
        question = req.question.strip()
        if not question:
            raise HTTPException(status_code=400, detail="Question cannot be empty")
        if session.user_simulator is None:
            raise HTTPException(status_code=500, detail="User simulator is unavailable")
        try:
            response = session.user_simulator.respond(question)
            info = dict(getattr(session.user_simulator, "last_response_info", {}) or {})
            turn = {
                "question": question,
                "response": response,
                "response_info": info,
                "ts": time.time(),
            }
            with state.lock:
                session.user_turns.append(turn)
            return {"status": "ok", "turn": turn, "user_turns": session.user_turns}
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Ask user failed: {exc}") from exc

    @app.post("/api/session/{session_id}/eval")
    def evaluate(session_id: str, request: Request):
        state: AnnotatorState = app.state.annotator
        session = _session_or_404(state, session_id)
        session.last_result = _evaluate_session(session)
        session.last_eval_at = time.time()
        return _session_payload(session, request=request)

    @app.post("/api/session/{session_id}/finish")
    def finish(session_id: str, request: Request):
        state: AnnotatorState = app.state.annotator
        session = _session_or_404(state, session_id)
        with state.lock:
            session.last_result = _evaluate_session(session)
            session.last_eval_at = time.time()
            payload = _session_payload(session, request=request)
            _finalize_session(session)
            state.sessions.pop(session.id, None)
            return payload

    @app.get("/vnc/{vnc_port}")
    def vnc_index(vnc_port: int):
        return RedirectResponse(url=f"/vnc/{vnc_port}/vnc.html")

    @app.get("/vnc/{vnc_port}/{path:path}")
    def proxy_vnc_http(vnc_port: int, path: str, request: Request):
        state: AnnotatorState = app.state.annotator
        _require_vnc_port(state, vnc_port)
        target = _vnc_http_target(vnc_port, path, request.url.query)
        try:
            proxied = urllib.request.Request(target, headers={"User-Agent": "GMA Annotator"})
            with urllib.request.urlopen(proxied, timeout=20) as resp:
                content = resp.read()
                headers = {"Cache-Control": "no-store"}
                content_type = resp.headers.get("Content-Type")
                if content_type:
                    headers["Content-Type"] = content_type
                return Response(content=content, status_code=resp.status, headers=headers)
        except urllib.error.HTTPError as exc:
            detail = exc.read()
            return Response(content=detail, status_code=exc.code)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"VNC proxy failed: {exc}") from exc

    @app.websocket("/vnc/{vnc_port}/websockify")
    async def proxy_vnc_websocket(vnc_port: int, websocket: WebSocket):
        state: AnnotatorState = app.state.annotator
        if state.token and _supplied_ws_token(websocket) != state.token:
            await websocket.close(code=1008)
            return
        try:
            _require_vnc_port(state, vnc_port)
        except HTTPException:
            await websocket.close(code=1008)
            return

        await websocket.accept()
        target = f"ws://127.0.0.1:{vnc_port}/websockify"
        try:
            async with websockets.connect(target, max_size=None) as upstream:
                await _bridge_websockets(websocket, upstream)
        except Exception:
            with contextlib.suppress(Exception):
                await websocket.close(code=1011)

    return app


def _default_task_dirs() -> list[str]:
    gma_dir = Path(__file__).resolve().parents[1] / "tasks" / "definitions" / "GMA"
    return [str(gma_dir)] if gma_dir.exists() else []


def _default_config_path() -> Path:
    repo_root = Path(__file__).resolve().parents[3]
    config_path = repo_root / "configs" / "default.toml"
    return config_path if config_path.exists() else Path("configs/default.toml")


def _user_simulator_kwargs() -> dict[str, Any]:
    config = load_config(_default_config_path())
    agent_config = resolve_agent_config(config)
    simulator = config.user_simulator
    return {
        "model_name": simulator.model or agent_config.model,
        "llm_base_url": simulator.base_url or agent_config.base_url,
        "api_key": simulator.api_key or agent_config.api_key,
        "temperature": simulator.temperature,
        "max_tokens": simulator.max_tokens,
        "timeout": simulator.timeout,
        "retries": simulator.retries,
    }


def _supplied_token(request: Request) -> str | None:
    return (
        request.headers.get("x-gma-token")
        or request.query_params.get("token")
        or request.cookies.get("gma_token")
    )


def _supplied_ws_token(websocket: WebSocket) -> str | None:
    return (
        websocket.headers.get("x-gma-token")
        or websocket.query_params.get("token")
        or websocket.cookies.get("gma_token")
    )


async def _bridge_websockets(client: WebSocket, upstream) -> None:
    async def client_to_upstream() -> None:
        while True:
            message = await client.receive()
            msg_type = message.get("type")
            if msg_type == "websocket.disconnect":
                await upstream.close()
                return
            if message.get("bytes") is not None:
                await upstream.send(message["bytes"])
            elif message.get("text") is not None:
                await upstream.send(message["text"])

    async def upstream_to_client() -> None:
        async for message in upstream:
            if isinstance(message, bytes):
                await client.send_bytes(message)
            else:
                await client.send_text(message)

    tasks = [
        asyncio.create_task(client_to_upstream()),
        asyncio.create_task(upstream_to_client()),
    ]
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for task in pending:
        task.cancel()
    for task in done:
        task.result()
    for task in pending:
        with contextlib.suppress(asyncio.CancelledError):
            await task


def _vnc_http_target(vnc_port: int, path: str, query: str) -> str:
    target = f"http://127.0.0.1:{vnc_port}/{path or 'vnc.html'}"
    if query:
        target = f"{target}?{query}"
    return target


def _visible_containers() -> list[dict[str, Any]]:
    return [container for container in discover_containers() if _container_is_visible(container)]


def _container_is_visible(container: dict[str, Any]) -> bool:
    env_id = _container_env_id(container)
    return env_id in VISIBLE_ENV_IDS


def _container_env_id(container: dict[str, Any]) -> int | None:
    name = str(container.get("name") or "")
    prefix = "gma_env_"
    if name.startswith(prefix):
        suffix = name[len(prefix) :]
        if suffix.isdigit():
            return int(suffix)
    backend_port = container.get("backend_port") or _url_port(container.get("backend_url"))
    if backend_port is not None and backend_port >= BASE_BACKEND_PORT:
        return backend_port - BASE_BACKEND_PORT
    return None


def _backend_url_is_visible(url: str) -> bool:
    port = _url_port(url)
    if port is None or port < BASE_BACKEND_PORT:
        return False
    return (port - BASE_BACKEND_PORT) in VISIBLE_ENV_IDS


def _vnc_port_is_visible(vnc_port: int | None) -> bool:
    if vnc_port is None or vnc_port < BASE_VNC_PORT:
        return False
    return (vnc_port - BASE_VNC_PORT) in VISIBLE_ENV_IDS


def _display_path(path: Path) -> str:
    repo_root = Path(__file__).resolve().parents[3]
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _require_vnc_port(state: AnnotatorState, vnc_port: int) -> None:
    if vnc_port < 1 or vnc_port > 65535:
        raise HTTPException(status_code=404, detail="Unknown VNC environment")
    allowed = _allowed_vnc_ports(state)
    if vnc_port not in allowed:
        raise HTTPException(status_code=404, detail="Unknown VNC environment")


def _allowed_vnc_ports(state: AnnotatorState) -> set[int]:
    ports: set[int] = set()
    for container in _visible_containers():
        port = container.get("vnc_port")
        if port:
            ports.add(int(port))
    if state.default_url and _backend_url_is_visible(state.default_url):
        port = _infer_vnc_port_from_backend_port(_url_port(state.default_url))
        if port:
            ports.add(port)
    with state.lock:
        for session in state.sessions.values():
            if session.vnc_port and _vnc_port_is_visible(session.vnc_port):
                ports.add(session.vnc_port)
    return ports


def _session_or_404(state: AnnotatorState, session_id: str) -> AnnotationSession:
    with state.lock:
        session = state.sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


def _session_key(*, url: str | None, device: str) -> tuple[str | None, str]:
    return (url.rstrip("/") if url else None, device)


def _find_session(
    state: AnnotatorState,
    *,
    url: str | None,
    device: str,
) -> AnnotationSession | None:
    if url is None:
        return next(iter(state.sessions.values()), None)
    normalized = url.rstrip("/")
    for session in state.sessions.values():
        if session.url.rstrip("/") == normalized and session.device == device:
            return session
    return None


def _evaluate_session(session: AnnotationSession) -> EvalResult:
    return session.task.evaluate(session.client)


def _finalize_session(session: AnnotationSession) -> None:
    try:
        session.task.finalize(session.client)
    except Exception:
        pass


def _environment_payload(container: dict[str, Any], *, request: Request) -> dict[str, Any]:
    backend_url = container["backend_url"]
    vnc_port = container.get("vnc_port") or _infer_vnc_port_from_backend_port(
        container.get("backend_port") or _url_port(backend_url)
    )
    return {
        "name": container.get("name") or "container",
        "url": backend_url,
        "backend_port": container.get("backend_port"),
        "vnc_port": vnc_port,
        "vnc_proxy_url": _build_vnc_proxy_url(vnc_port) if vnc_port else None,
        "image": container.get("image"),
    }


def _session_payload(session: AnnotationSession, *, request: Request | None = None) -> dict[str, Any]:
    return {
        "id": session.id,
        "task": {
            "name": session.task.name,
            "goal": session.task.goal,
            "apps": sorted(session.task.apps),
            "tags": sorted(session.task.tags),
            "snapshot": session.task.snapshot,
            "assets": len(session.task.assets),
        },
        "environment": {
            "url": session.url,
            "device": session.device,
            "container_name": session.container_name,
            "vnc_port": session.vnc_port,
            "vnc_proxy_url": _build_vnc_proxy_url(session.vnc_port) if session.vnc_port else None,
        },
        "started_at": session.started_at,
        "last_eval_at": session.last_eval_at,
        "user_turns": session.user_turns,
        "result": _result_payload(session.last_result),
    }


def _result_payload(result: EvalResult | None) -> dict[str, Any] | None:
    if result is None:
        return None
    return {
        "score": result.score,
        "passed": result.passed,
        "summary": result.summary,
        "criteria": [
            {
                "name": item.name,
                "passed": item.passed,
                "score": item.score,
                "reason": item.reason,
                "weight": item.weight,
            }
            for item in result.criterion_results
        ],
    }


def _vnc_port_for_backend_url(backend_url: str) -> int | None:
    normalized = backend_url.rstrip("/")
    for container in _visible_containers():
        if container.get("backend_url", "").rstrip("/") == normalized:
            return container.get("vnc_port") or _infer_vnc_port_from_backend_port(
                container.get("backend_port")
            )
    port = _infer_vnc_port_from_backend_port(_url_port(backend_url))
    return port if _vnc_port_is_visible(port) else None


def _url_port(url: str | None) -> int | None:
    if not url:
        return None
    parsed = urllib.parse.urlparse(url if "://" in url else f"http://{url}")
    if parsed.port:
        return parsed.port
    if parsed.scheme == "http":
        return 80
    if parsed.scheme == "https":
        return 443
    return None


def _infer_vnc_port_from_backend_port(backend_port: int | None) -> int | None:
    if backend_port is None or backend_port < BASE_BACKEND_PORT:
        return None
    return BASE_VNC_PORT + (backend_port - BASE_BACKEND_PORT)


def _build_vnc_proxy_url(vnc_port: int | None) -> str | None:
    if not vnc_port:
        return None
    websocket_path = f"vnc/{vnc_port}/websockify"
    params = urllib.parse.urlencode(
        {
            "autoconnect": "1",
            "resize": "scale",
            "path": websocket_path,
        }
    )
    return f"/vnc/{vnc_port}/vnc.html?{params}"


def start_server(
    *,
    host: str = "0.0.0.0",
    port: int = 7860,
    default_url: str | None = None,
    default_device: str = "emulator-5554",
    task_dirs: list[str] | None = None,
    token: str | None = None,
) -> None:
    app = create_app(
        default_url=default_url,
        default_device=default_device,
        task_dirs=task_dirs,
        token=token,
    )
    uvicorn.run(app, host=host, port=port, log_level="info")


INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GMA Annotation</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --line: #d8dde6;
      --text: #17202a;
      --muted: #596579;
      --accent: #166b5b;
      --accent-dark: #0e4f43;
      --danger: #a33a2b;
      --warning: #8b6514;
      --ok: #176b38;
      --shadow: 0 8px 24px rgba(30, 40, 55, 0.08);
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 14px;
    }

    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      min-height: 58px;
      padding: 10px 18px;
      border-bottom: 1px solid var(--line);
      background: #ffffff;
    }

    h1 {
      margin: 0;
      font-size: 18px;
      font-weight: 700;
      letter-spacing: 0;
    }

    .status {
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--muted);
      white-space: nowrap;
    }

    .dot {
      width: 9px;
      height: 9px;
      border-radius: 50%;
      background: #9099a8;
    }

    .dot.ready {
      background: var(--ok);
    }

    .dot.busy {
      background: var(--warning);
    }

    .dot.error {
      background: var(--danger);
    }

    .toolbar {
      display: grid;
      grid-template-columns: minmax(200px, 310px) minmax(260px, 1fr) auto auto auto;
      gap: 10px;
      align-items: end;
      padding: 12px 18px;
      border-bottom: 1px solid var(--line);
      background: #fbfcfe;
    }

    label {
      display: grid;
      gap: 4px;
      min-width: 0;
      color: var(--muted);
      font-size: 12px;
      font-weight: 650;
    }

    select,
    input,
    textarea,
    button {
      font: inherit;
    }

    select,
    input,
    textarea {
      width: 100%;
      min-height: 38px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px 10px;
      background: #ffffff;
      color: var(--text);
    }

    textarea {
      min-height: 92px;
      resize: vertical;
      line-height: 1.45;
    }

    button {
      min-height: 38px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px 12px;
      background: #ffffff;
      color: var(--text);
      cursor: pointer;
      font-weight: 650;
    }

    button.primary {
      border-color: var(--accent);
      background: var(--accent);
      color: #ffffff;
    }

    button.primary:hover {
      background: var(--accent-dark);
    }

    button.danger {
      border-color: #cfb0aa;
      color: var(--danger);
    }

    button:disabled {
      cursor: not-allowed;
      opacity: 0.55;
    }

    main {
      display: grid;
      grid-template-columns: minmax(420px, 1fr) 380px;
      gap: 16px;
      padding: 16px 18px 18px;
      min-height: calc(100vh - 124px);
    }

    .vnc-shell,
    .side-panel {
      min-width: 0;
    }

    .vnc-shell {
      display: grid;
      grid-template-rows: auto auto;
      align-content: start;
      gap: 12px;
    }

    .vnc-frame {
      min-height: calc(100vh - 160px);
      height: calc(100vh - 160px);
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #151a21;
      box-shadow: var(--shadow);
      overflow: hidden;
      position: relative;
    }

    #vnc {
      width: 100%;
      height: 100%;
      border: 0;
      display: block;
      background: #151a21;
    }

    #vnc[hidden],
    .empty-vnc[hidden] {
      display: none !important;
    }

    .empty-vnc {
      display: grid;
      place-items: center;
      height: 100%;
      padding: 24px;
      color: #c8d0dc;
      font-weight: 650;
      text-align: center;
    }

    .side-panel {
      display: grid;
      grid-template-rows: auto auto auto auto auto 1fr;
      gap: 12px;
    }

    .panel {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      box-shadow: var(--shadow);
      padding: 12px;
    }

    .grid {
      display: grid;
      gap: 8px;
    }

    .goal {
      display: grid;
      gap: 8px;
    }

    .goal h2,
    .panel h2 {
      margin: 0;
      font-size: 14px;
      font-weight: 750;
      letter-spacing: 0;
    }

    .goal p {
      margin: 0;
      line-height: 1.45;
    }

    .meta {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      color: var(--muted);
      font-size: 12px;
    }

    .pill {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 3px 8px;
      background: #f7f9fb;
    }

    .button-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
    }

    .wide {
      grid-column: 1 / -1;
    }

    .result {
      min-height: 190px;
      overflow: auto;
    }

    pre {
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      margin: 8px 0 0;
      color: #26313f;
      font-size: 12px;
      line-height: 1.45;
    }

    .user-turns {
      max-height: 150px;
      overflow: auto;
      padding: 8px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #f7f9fb;
    }

    .task-code {
      min-height: 140px;
      max-height: 320px;
      overflow: auto;
      white-space: pre;
      overflow-wrap: normal;
      padding: 8px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #0f1720;
      color: #e5edf7;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
      font-size: 11px;
      line-height: 1.45;
    }

    @media (max-width: 980px) {
      .toolbar {
        grid-template-columns: 1fr;
      }

      main {
        grid-template-columns: 1fr;
      }

      .vnc-frame {
        min-height: 68vh;
        height: 68vh;
      }
    }
  </style>
</head>
<body>
  <header>
    <h1>GMA Annotation</h1>
    <div class="status"><span id="status-dot" class="dot"></span><span id="status-text">Idle</span></div>
  </header>

  <section class="toolbar">
    <label>Environment
      <select id="environment"></select>
    </label>
    <label>Task
      <select id="task"></select>
    </label>
    <button id="start" class="primary">Start</button>
    <button id="restart">Restart</button>
    <button id="finish" class="danger" disabled>Finish</button>
  </section>

  <main>
    <section class="vnc-shell">
      <div class="vnc-frame">
        <iframe id="vnc" title="Device VNC" allow="fullscreen; clipboard-read; clipboard-write" hidden></iframe>
        <div id="empty-vnc" class="empty-vnc">No VNC display available.</div>
      </div>

      <section class="panel grid">
        <h2>Task Code</h2>
        <div id="task-code-path" class="meta"></div>
        <pre id="task-code" class="task-code">Select a task to view code.</pre>
      </section>
    </section>

    <aside class="side-panel">
      <section class="panel goal">
        <h2 id="task-name">Task</h2>
        <p id="goal-text">Select a task and start a session.</p>
        <div id="task-meta" class="meta"></div>
      </section>

      <section class="panel grid">
        <h2>Evaluation</h2>
        <div class="button-grid">
          <button id="refresh-vnc">Reload VNC</button>
          <button id="eval">Evaluate</button>
        </div>
      </section>

      <section class="panel grid">
        <h2>Ask User</h2>
        <label>Question
          <input id="user-question" autocomplete="off">
        </label>
        <div class="button-grid">
          <button id="ask-user" class="wide">Ask User</button>
        </div>
        <pre id="user-turns" class="user-turns">No user questions yet.</pre>
      </section>

      <section class="panel grid">
        <h2>Paste</h2>
        <label>Content
          <textarea id="paste-input" autocomplete="off" spellcheck="false"></textarea>
        </label>
        <div class="button-grid">
          <button id="paste-text" class="wide">Paste to Emulator</button>
        </div>
      </section>

      <section class="panel grid">
        <h2>Submission</h2>
        <label>Text
          <input id="text-input" autocomplete="off">
        </label>
        <div class="button-grid">
          <button id="send-answer">Answer</button>
          <button id="mark-complete">Complete</button>
          <button id="mark-infeasible" class="wide">Infeasible</button>
        </div>
      </section>

      <section class="panel result">
        <h2>Result</h2>
        <pre id="result">No result yet.</pre>
      </section>
    </aside>
  </main>

  <script>
    const state = {
      token: new URLSearchParams(location.search).get("token") || localStorage.getItem("gma_token") || "",
      sessionId: null,
      busy: false,
      environments: [],
      tasks: [],
      selectedVncUrl: "",
      userTurns: [],
    };

    if (state.token) {
      localStorage.setItem("gma_token", state.token);
      document.cookie = "gma_token=" + encodeURIComponent(state.token) + "; path=/; SameSite=Lax";
    }

    const el = {
      dot: document.getElementById("status-dot"),
      status: document.getElementById("status-text"),
      environment: document.getElementById("environment"),
      task: document.getElementById("task"),
      start: document.getElementById("start"),
      restart: document.getElementById("restart"),
      finish: document.getElementById("finish"),
      vnc: document.getElementById("vnc"),
      emptyVnc: document.getElementById("empty-vnc"),
      taskName: document.getElementById("task-name"),
      goalText: document.getElementById("goal-text"),
      taskMeta: document.getElementById("task-meta"),
      taskCodePath: document.getElementById("task-code-path"),
      taskCode: document.getElementById("task-code"),
      result: document.getElementById("result"),
      textInput: document.getElementById("text-input"),
      pasteInput: document.getElementById("paste-input"),
      pasteText: document.getElementById("paste-text"),
      userQuestion: document.getElementById("user-question"),
      askUser: document.getElementById("ask-user"),
      userTurns: document.getElementById("user-turns"),
      refreshVnc: document.getElementById("refresh-vnc"),
      eval: document.getElementById("eval"),
      sendAnswer: document.getElementById("send-answer"),
      markComplete: document.getElementById("mark-complete"),
      markInfeasible: document.getElementById("mark-infeasible"),
    };

    function headers() {
      const h = {"Content-Type": "application/json"};
      if (state.token) h["x-gma-token"] = state.token;
      return h;
    }

    async function api(path, options = {}) {
      const response = await fetch(path, {
        ...options,
        headers: {...headers(), ...(options.headers || {})},
      });
      if (!response.ok) {
        let detail = response.statusText;
        try {
          detail = (await response.json()).detail || detail;
        } catch (_) {}
        throw new Error(detail);
      }
      return response.json();
    }

    function setStatus(text, kind = "") {
      el.status.textContent = text;
      el.dot.className = "dot" + (kind ? " " + kind : "");
    }

    function setBusy(value, text = "Working") {
      state.busy = value;
      [
        el.environment,
        el.task,
        el.start,
        el.restart,
        el.eval,
        el.refreshVnc,
        el.textInput,
        el.pasteInput,
        el.pasteText,
        el.userQuestion,
        el.askUser,
        el.sendAnswer,
        el.markComplete,
        el.markInfeasible,
      ].forEach((node) => {
        node.disabled = value;
      });
      el.finish.disabled = value || !state.sessionId;
      setStatus(value ? text : (state.sessionId ? "Ready" : "Idle"), value ? "busy" : (state.sessionId ? "ready" : ""));
    }

    function showError(error) {
      setStatus(error.message || String(error), "error");
      el.result.textContent = error.message || String(error);
    }

    function isSessionNotFound(error) {
      return (error.message || String(error) || "").includes("Session not found");
    }

    async function recoverMissingSession(error) {
      if (!isSessionNotFound(error)) return false;
      const targetUrl = el.environment.value || null;
      state.sessionId = null;
      el.finish.disabled = true;
      try {
        const sessions = await api("/api/sessions");
        const available = sessions.sessions || [];
        const matching = available.find((session) => {
          return targetUrl && session.environment && session.environment.url === targetUrl;
        });
        if (matching) {
          applySession(matching);
          setStatus("Session refreshed", "ready");
          return true;
        }
        setStatus("Session ended", "");
        el.result.textContent = "Session ended. Start a new task session to continue.";
        renderSelectedTaskSummary();
        return true;
      } catch (_) {
        showError(error);
        return true;
      }
    }

    function fillSelect(select, items, labelFn, valueFn) {
      select.innerHTML = "";
      for (const item of items) {
        const option = document.createElement("option");
        option.value = valueFn(item);
        option.textContent = labelFn(item);
        select.appendChild(option);
      }
    }

    async function loadInitialData() {
      try {
        const [envs, tasks, sessions] = await Promise.all([
          api("/api/environments"),
          api("/api/tasks"),
          api("/api/sessions"),
        ]);
        state.environments = envs.environments;
        state.tasks = tasks.tasks;
        fillSelect(
          el.environment,
          state.environments,
          (item) => item.name + " (" + item.url + ")",
          (item) => item.url
        );
        fillSelect(
          el.task,
          tasks.tasks,
          (item) => item.name,
          (item) => item.name
        );
        el.task.title = (tasks.task_dirs && tasks.task_dirs.length)
          ? "Scoped to: " + tasks.task_dirs.join(", ")
          : "All built-in tasks";
        applySelectedEnvironment();
        renderSelectedTaskSummary();
        loadSelectedTaskCode();
        if (sessions.sessions.length) {
          applySession(sessions.sessions[0]);
        } else {
          setStatus("Idle");
        }
      } catch (error) {
        showError(error);
      }
    }

    function selectedEnvironment() {
      return state.environments.find((item) => item.url === el.environment.value) || null;
    }

    function applySelectedEnvironment() {
      const env = selectedEnvironment();
      const url = env && env.vnc_proxy_url ? env.vnc_proxy_url : "";
      setVncFrame(url);
    }

    function selectedTask() {
      return state.tasks.find((item) => item.name === el.task.value) || null;
    }

    function renderSelectedTaskSummary() {
      if (state.sessionId) return;
      const task = selectedTask();
      el.taskName.textContent = task ? task.name : "Task";
      el.goalText.textContent = task ? task.goal : "Select a task and start a session.";
      el.taskMeta.innerHTML = "";
      for (const text of task ? task.apps || [] : []) {
        const span = document.createElement("span");
        span.className = "pill";
        span.textContent = text;
        el.taskMeta.appendChild(span);
      }
    }

    async function loadSelectedTaskCode() {
      const taskName = el.task.value;
      if (!taskName) {
        el.taskCodePath.innerHTML = "";
        el.taskCode.textContent = "Select a task to view code.";
        return;
      }
      el.taskCodePath.innerHTML = "";
      el.taskCode.textContent = "Loading task code...";
      try {
        const payload = await api("/api/task/" + encodeURIComponent(taskName) + "/code");
        el.taskCodePath.innerHTML = "";
        const span = document.createElement("span");
        span.className = "pill";
        span.textContent = payload.path || taskName;
        el.taskCodePath.appendChild(span);
        el.taskCode.textContent = payload.code || "";
      } catch (error) {
        el.taskCode.textContent = "Failed to load task code: " + (error.message || String(error));
      }
    }

    function vncUrlWithReloadToken(url) {
      if (!url) return "";
      const glue = url.includes("?") ? "&" : "?";
      return url + glue + "reload=" + Date.now();
    }

    function setVncFrame(url, forceReload = false) {
      state.selectedVncUrl = url || "";
      if (!url) {
        el.vnc.hidden = true;
        el.emptyVnc.hidden = false;
        el.emptyVnc.textContent = "No VNC display available.";
        return;
      }
      el.emptyVnc.hidden = true;
      el.vnc.hidden = false;
      const nextUrl = forceReload ? vncUrlWithReloadToken(url) : url;
      const absolute = new URL(nextUrl, location.href).href;
      if (forceReload || el.vnc.src !== absolute) {
        el.vnc.src = nextUrl;
      }
    }

    function reloadVnc() {
      if (!state.selectedVncUrl) return;
      setVncFrame(state.selectedVncUrl, true);
    }

    function applySession(payload) {
      state.sessionId = payload.id;
      el.finish.disabled = false;
      if (payload.environment && payload.environment.url) {
        el.environment.value = payload.environment.url;
      }
      if (payload.environment && payload.environment.vnc_proxy_url) {
        setVncFrame(payload.environment.vnc_proxy_url, true);
      } else {
        applySelectedEnvironment();
      }
      el.taskName.textContent = payload.task.name;
      el.goalText.textContent = payload.task.goal;
      if ([...el.task.options].some((option) => option.value === payload.task.name)) {
        el.task.value = payload.task.name;
      }
      state.userTurns = payload.user_turns || [];
      el.taskMeta.innerHTML = "";
      const meta = [
        payload.environment.container_name || payload.environment.url,
        payload.task.snapshot,
        "assets " + payload.task.assets,
        ...payload.task.apps,
      ];
      for (const text of meta.filter(Boolean)) {
        const span = document.createElement("span");
        span.className = "pill";
        span.textContent = text;
        el.taskMeta.appendChild(span);
      }
      renderUserTurns();
      renderResult(payload.result);
      loadSelectedTaskCode();
      setStatus("Ready", "ready");
    }

    function renderResult(result) {
      if (!result) {
        el.result.textContent = "No result yet.";
        return;
      }
      const status = result.passed ? "PASS" : "FAIL";
      const lines = [status + " score=" + result.score.toFixed(2), result.summary || ""];
      for (const item of result.criteria || []) {
        const itemStatus = item.passed ? "PASS" : "FAIL";
        lines.push("[" + itemStatus + "] " + item.name + " (" + item.score.toFixed(2) + ", w=" + item.weight + "): " + item.reason);
      }
      el.result.textContent = lines.filter(Boolean).join("\n");
    }

    function renderUserTurns() {
      if (!state.userTurns || !state.userTurns.length) {
        el.userTurns.textContent = "No user questions yet.";
        return;
      }
      const lines = [];
      for (const turn of state.userTurns) {
        const info = turn.response_info || {};
        const answer = info.should_respond === false ? "[no response]" : (turn.response || "[empty]");
        lines.push("Q: " + turn.question);
        lines.push("User: " + answer + " (" + (info.source || "unknown") + ")");
      }
      el.userTurns.textContent = lines.join("\n\n");
      el.userTurns.scrollTop = el.userTurns.scrollHeight;
    }

    async function startSession(force = false) {
      const targetUrl = el.environment.value || null;
      setBusy(true, force ? "Restarting" : "Starting");
      try {
        const payload = await api("/api/session/start", {
          method: "POST",
          body: JSON.stringify({
            task_name: el.task.value,
            url: targetUrl,
            force,
          }),
        });
        if (payload.starting) {
          await waitForStartingSession(targetUrl);
        } else {
          applySession(payload);
        }
      } catch (error) {
        if ((error.message || "").includes("already starting")) {
          await waitForStartingSession(targetUrl);
        } else {
          showError(error);
        }
      } finally {
        setBusy(false);
      }
    }

    async function waitForStartingSession(targetUrl) {
      setStatus("Starting", "busy");
      for (let attempt = 0; attempt < 120; attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, 5000));
        const sessions = await api("/api/sessions");
        const matching = (sessions.sessions || []).find((session) => {
          return !targetUrl || (session.environment && session.environment.url === targetUrl);
        });
        if (matching) {
          applySession(matching);
          return;
        }
        const health = await api("/api/health");
        const failed = (health.start_errors || []).find((item) => {
          return !targetUrl || item.url === targetUrl;
        });
        if (failed) {
          throw new Error(failed.detail || "Task initialization failed.");
        }
        if (!health.starting_sessions) {
          throw new Error("Task initialization finished but no active session was created.");
        }
      }
      throw new Error("Task initialization is still running. Try refreshing in a moment.");
    }

    async function finishSession() {
      if (!state.sessionId) return;
      setBusy(true, "Finishing");
      try {
        const payload = await api("/api/session/" + state.sessionId + "/finish", {method: "POST"});
        renderResult(payload.result);
        state.sessionId = null;
        el.finish.disabled = true;
        setStatus("Idle");
      } catch (error) {
        if (!(await recoverMissingSession(error))) showError(error);
      } finally {
        setBusy(false);
      }
    }

    async function evaluate() {
      if (!state.sessionId) return;
      setBusy(true, "Evaluating");
      try {
        const payload = await api("/api/session/" + state.sessionId + "/eval", {method: "POST"});
        applySession(payload);
      } catch (error) {
        if (!(await recoverMissingSession(error))) showError(error);
      } finally {
        setBusy(false);
      }
    }

    async function sendAction(action) {
      if (!state.sessionId || state.busy) return;
      setBusy(true, "Submitting");
      try {
        await api("/api/session/" + state.sessionId + "/action", {
          method: "POST",
          body: JSON.stringify({action}),
        });
        setStatus("Ready", "ready");
      } catch (error) {
        if (!(await recoverMissingSession(error))) showError(error);
      } finally {
        setBusy(false);
      }
    }

    async function pasteText() {
      if (!state.sessionId || state.busy) return;
      const text = el.pasteInput.value;
      if (!text) return;
      setBusy(true, "Pasting");
      try {
        const payload = await api("/api/session/" + state.sessionId + "/paste", {
          method: "POST",
          body: JSON.stringify({text}),
        });
        setStatus("Pasted " + payload.chars + " chars", "ready");
      } catch (error) {
        if (!(await recoverMissingSession(error))) showError(error);
      } finally {
        setBusy(false);
      }
    }

    async function askUser() {
      if (!state.sessionId || state.busy) return;
      const question = el.userQuestion.value.trim();
      if (!question) return;
      setBusy(true, "Asking User");
      try {
        const payload = await api("/api/session/" + state.sessionId + "/ask_user", {
          method: "POST",
          body: JSON.stringify({question}),
        });
        state.userTurns = payload.user_turns || [];
        renderUserTurns();
        setStatus("Ready", "ready");
      } catch (error) {
        if (!(await recoverMissingSession(error))) showError(error);
      } finally {
        setBusy(false);
      }
    }

    el.environment.addEventListener("change", applySelectedEnvironment);
    el.task.addEventListener("change", () => {
      renderSelectedTaskSummary();
      loadSelectedTaskCode();
    });
    el.start.addEventListener("click", () => startSession(false));
    el.restart.addEventListener("click", () => startSession(true));
    el.finish.addEventListener("click", finishSession);
    el.refreshVnc.addEventListener("click", reloadVnc);
    el.eval.addEventListener("click", evaluate);
    el.askUser.addEventListener("click", askUser);
    el.pasteText.addEventListener("click", pasteText);
    el.sendAnswer.addEventListener("click", () => sendAction({action_type: "answer", text: el.textInput.value}));
    el.markComplete.addEventListener("click", () => sendAction({action_type: "status", goal_status: "complete"}));
    el.markInfeasible.addEventListener("click", () => sendAction({action_type: "status", goal_status: "infeasible"}));
    el.pasteInput.addEventListener("keydown", (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
        event.preventDefault();
        pasteText();
      }
    });
    el.textInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        sendAction({action_type: "answer", text: el.textInput.value});
      }
    });
    el.userQuestion.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        askUser();
      }
    });

    loadInitialData();
  </script>
</body>
</html>
"""
