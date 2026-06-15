"""Parallel task execution runner.

Distributes tasks across Docker containers, runs agent loops, evaluates
results, and logs trajectories.
"""

from __future__ import annotations

import os
import random
import subprocess
import threading
import time
from dataclasses import dataclass
from queue import Empty, Queue
from typing import Any

from joblib import Parallel, delayed
from loguru import logger

from gma.agents.base import BaseAgent
from gma.agents.registry import create_agent
from gma.agents.user_simulator import UserSimulator
from gma.logging.trajectory import TrajectoryLogger, scan_finished_tasks
from gma.runtime.client import GMAClient
from gma.runtime.docker import discover_backend_urls
from gma.runtime.models import Action, ActionType, Observation
from gma.apps import get_package
from gma.tasks.base import BaseTask
from gma.tasks.registry import TaskRegistry


@dataclass
class TaskResult:
    """Result of executing a single task."""

    task_name: str
    score: float | None = None
    steps: int = 0
    duration: float = 0.0
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.score is not None and self.score >= 1.0


@dataclass(frozen=True)
class EnvironmentLease:
    """One reusable backend environment in the evaluation pool."""

    client: GMAClient
    container_name: str


# ---------------------------------------------------------------------------
# Single-task execution
# ---------------------------------------------------------------------------


def _execute_task(
    client: GMAClient,
    agent: BaseAgent,
    task: BaseTask,
    max_steps: int,
    traj: TrajectoryLogger,
    evaluate_each_step: bool = True,
    user_simulator_kwargs: dict[str, Any] | None = None,
) -> tuple[int, float]:
    """Run one task to completion. Returns (steps, score)."""

    def _evaluate(step: int, phase: str):
        result = task.evaluate(client)
        traj.log_evaluation(
            step=step,
            phase=phase,
            score=result.score,
            passed=result.passed,
            summary=result.summary,
            criterion_results=[
                {
                    "name": cr.name,
                    "passed": cr.passed,
                    "score": cr.score,
                    "reason": cr.reason,
                    "weight": cr.weight,
                }
                for cr in result.criterion_results
            ],
        )
        return result

    # Initialize task (load snapshot + setup)
    if not task.initialize(client):
        raise RuntimeError(f"Task {task.name} initialization failed")

    app_context = {
        app_name: package
        for app_name in sorted(task.apps)
        if (package := get_package(app_name))
    }
    try:
        agent.on_task_start(task.goal, app_context=app_context)
    except TypeError:
        agent.on_task_start(task.goal)
    user_simulator = UserSimulator.from_task(task, **(user_simulator_kwargs or {}))

    # Log metadata
    traj.log_metadata({
        "task_name": task.name,
        "goal": task.goal,
        "apps": sorted(task.apps),
        "tags": sorted(task.tags),
    })

    # Agent loop
    step = 0
    obs = Observation(screenshot=client.screenshot(wait=True))
    last_result = _evaluate(step=0, phase="post_initialize")
    if last_result.passed:
        task.finalize(client)
        agent.on_task_end()
        traj.log_score(last_result.score, last_result.summary)
        return step, last_result.score

    while step < max_steps:
        step += 1
        action = agent.act(obs)
        action_payload = action.model_dump(exclude_none=True)

        if action.action_type == ActionType.CALL_USER:
            question = action.text or "Please provide the missing information."
            user_response = user_simulator.respond(question)
            response_info = dict(getattr(user_simulator, "last_response_info", {}) or {})
            logger.info(f"call_user question: {question}")
            logger.info(
                "simulated user response "
                f"({response_info.get('source', 'unknown')}): {user_response}"
            )
            traj.log_user_simulator(
                step=step,
                question=question,
                response=user_response,
                response_info=response_info,
            )
            agent.on_user_response(question, user_response)

            traj.log_step(
                step=step,
                observation=obs,
                action=action_payload,
                agent_stats=agent.stats,
            )

            obs = Observation(
                screenshot=client.screenshot(wait=True),
                metadata={
                    "last_user_question": question,
                    "last_user_response": user_response,
                    "last_user_response_source": response_info.get("source"),
                    "last_user_should_respond": response_info.get("should_respond"),
                },
            )
        else:
            traj.log_step(
                step=step,
                observation=obs,
                action=action_payload,
                agent_stats=agent.stats,
            )

            if action.is_terminal:
                logger.debug(f"Task {task.name}: terminal action at step {step}")
                # For ANSWER actions, still send to client (stores the answer)
                if action.action_type == ActionType.ANSWER:
                    client.step(action)
                    obs = Observation(screenshot=client.screenshot(wait=True))
            else:
                obs = client.execute_action(action)

        if evaluate_each_step:
            last_result = _evaluate(step=step, phase="post_action")
            if last_result.passed:
                logger.debug(f"Task {task.name}: passed at step {step}")
                break

        if action.is_terminal:
            break

    if not evaluate_each_step:
        last_result = _evaluate(step=step, phase="final")
    elif last_result is None:
        last_result = _evaluate(step=step, phase="final")

    traj.log_score(last_result.score, last_result.summary)

    # Teardown
    task.finalize(client)
    agent.on_task_end()

    return step, last_result.score


# ---------------------------------------------------------------------------
# Per-task worker (runs in a thread)
# ---------------------------------------------------------------------------


def _process_task(
    task_name: str,
    client_queue: Queue,
    agent_type: str,
    agent_kwargs: dict,
    user_simulator_kwargs: dict | None,
    task_registry: TaskRegistry,
    log_root: str,
    max_steps: int,
    retry_on_unhealthy: int = 2,
    evaluate_each_step: bool = True,
    reset_task_logs: bool = False,
    robust_env_recovery: bool = False,
    robust_env_max_task_retries: int = 3,
    robust_env_recovery_timeout: float = 420.0,
    robust_env_restart: bool = True,
) -> TaskResult:
    """Process a single task on an available environment."""

    traj = TrajectoryLogger(log_root, task_name)
    if reset_task_logs:
        traj.reset_task_dir()
    start = time.time()
    env_failures = 0

    while True:
        try:
            lease = _get_environment_lease(
                client_queue,
                timeout=robust_env_recovery_timeout + 60 if robust_env_recovery else None,
            )
        except Empty:
            message = "No evaluation environment became available"
            logger.error(f"Task {task_name} failed: {message}")
            return TaskResult(
                task_name=task_name,
                error=message,
                duration=time.time() - start,
            )

        client = lease.client
        returned_to_pool = False
        try:
            task = task_registry.get(task_name)
            agent = create_agent(agent_type, **agent_kwargs)

            attempts = 1 if robust_env_recovery else retry_on_unhealthy + 1
            for attempt in range(attempts):
                try:
                    steps, score = _execute_task(
                        client,
                        agent,
                        task,
                        max_steps,
                        traj,
                        evaluate_each_step=evaluate_each_step,
                        user_simulator_kwargs=user_simulator_kwargs,
                    )
                    client_queue.put(lease)
                    returned_to_pool = True
                    return TaskResult(
                        task_name=task_name,
                        score=score,
                        steps=steps,
                        duration=time.time() - start,
                    )
                except Exception as e:
                    if "not healthy" in str(e).lower() and attempt < attempts - 1:
                        logger.warning(f"Device unhealthy for {task_name}, retrying...")
                        time.sleep(20)
                        traj.reset()
                        continue
                    raise

        except Exception as e:
            if robust_env_recovery and _looks_like_environment_failure(client, e):
                env_failures += 1
                logger.warning(
                    f"Environment {lease.container_name} failed while running {task_name}; "
                    f"retrying task on another environment "
                    f"({env_failures}/{robust_env_max_task_retries})"
                )
                _recover_environment_async(
                    lease,
                    client_queue,
                    timeout=robust_env_recovery_timeout,
                    restart=robust_env_restart,
                )
                if env_failures <= robust_env_max_task_retries:
                    traj.reset()
                    continue
                logger.exception(f"Task {task_name} exceeded environment retry budget")
                return TaskResult(
                    task_name=task_name,
                    error=(
                        f"{e}; exceeded environment retry budget "
                        f"({robust_env_max_task_retries})"
                    ),
                    duration=time.time() - start,
                )

            logger.exception(f"Task {task_name} failed")
            client_queue.put(lease)
            returned_to_pool = True
            return TaskResult(
                task_name=task_name,
                error=str(e),
                duration=time.time() - start,
            )
        finally:
            # Healthy/task-level failures return the lease above. Environment
            # failures are recovered asynchronously and only re-enter the pool
            # after the backend becomes healthy again.
            if not returned_to_pool and not robust_env_recovery:
                client_queue.put(lease)


def _get_environment_lease(client_queue: Queue, timeout: float | None) -> EnvironmentLease:
    if timeout is None:
        return client_queue.get()
    return client_queue.get(timeout=timeout)


def _client_ready(client: GMAClient) -> bool:
    try:
        client.init()
        return client.health()
    except Exception:
        return False


def _looks_like_environment_failure(client: GMAClient, exc: Exception) -> bool:
    if not client.health():
        return True

    message = str(exc).lower()
    device_failure_markers = (
        "device is not healthy",
        "device emulator-5554 is not healthy",
        "device emulator-5554 did not become ready",
        "device 'emulator-5554' not found",
        "adb: device",
        "snapshot transition",
        "connection refused",
        "service unavailable",
    )
    return any(marker in message for marker in device_failure_markers)


def _recover_environment_async(
    lease: EnvironmentLease,
    client_queue: Queue,
    *,
    timeout: float,
    restart: bool,
) -> None:
    def recover() -> None:
        try:
            if restart and lease.container_name:
                logger.warning(f"Restarting evaluation container {lease.container_name}")
                result = subprocess.run(
                    ["docker", "restart", lease.container_name],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if result.returncode != 0:
                    raise RuntimeError(result.stderr.strip() or result.stdout.strip())

            deadline = time.time() + timeout
            while time.time() < deadline:
                if _client_ready(lease.client):
                    client_queue.put(lease)
                    logger.info(f"Recovered evaluation environment {lease.container_name}")
                    return
                time.sleep(5)
            raise TimeoutError(
                f"Timed out waiting for {lease.container_name} to become healthy"
            )
        except Exception as e:
            logger.exception(f"Failed to recover environment {lease.container_name}: {e}")

    thread = threading.Thread(
        target=recover,
        name=f"recover-{lease.container_name}",
        daemon=True,
    )
    thread.start()


def _initialize_environment_async(
    lease: EnvironmentLease,
    client_queue: Queue,
    *,
    timeout: float,
    restart: bool,
) -> None:
    if _client_ready(lease.client):
        client_queue.put(lease)
        return
    logger.warning(f"Environment {lease.container_name} is not ready at startup")
    _recover_environment_async(lease, client_queue, timeout=timeout, restart=restart)


def _default_container_name_for_url(
    url: str,
    index: int,
    *,
    container_prefix: str,
) -> str:
    try:
        port = int(url.rstrip("/").rsplit(":", 1)[1])
    except (IndexError, ValueError):
        return f"{container_prefix}_{index}"
    env_id = port - 8100
    if env_id >= 0:
        return f"{container_prefix}_{env_id}"
    return f"{container_prefix}_{index}"


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_evaluation(
    agent_type: str,
    agent_kwargs: dict,
    log_root: str,
    tasks: list[str] | None = None,
    max_steps: int = 50,
    backend_urls: list[str] | None = None,
    container_names: list[str] | None = None,
    container_image: str = "gma:latest",
    container_prefix: str = "gma_env",
    device: str = "emulator-5554",
    step_wait_time: float = 1.0,
    max_concurrency: int | None = None,
    shuffle: bool = False,
    extra_task_dirs: list[str] | None = None,
    evaluate_each_step: bool = True,
    skip_finished: bool = True,
    reset_task_logs: bool = False,
    user_simulator_kwargs: dict | None = None,
    robust_env_recovery: bool = False,
    robust_env_max_task_retries: int = 3,
    robust_env_recovery_timeout: float = 420.0,
    robust_env_restart: bool = True,
) -> list[TaskResult]:
    """Run evaluation across all tasks and containers.

    Args:
        agent_type: Registered agent name or path to agent file.
        agent_kwargs: Kwargs passed to agent constructor.
        log_root: Directory for trajectory logs.
        tasks: Specific task names to run. None = all tasks.
        max_steps: Max steps per task.
        backend_urls: Container backend URLs. None = auto-discover.
        container_image: Docker image filter for discovery.
        container_prefix: Container name prefix for discovery.
        device: Android device ID.
        step_wait_time: Wait time between steps.
        max_concurrency: Max parallel tasks. None = one per container.
        shuffle: Randomize task order.
        extra_task_dirs: Additional directories to scan for tasks.

    Returns:
        List of TaskResult for all tasks (finished + newly run).
    """
    # Discover containers
    if not backend_urls:
        backend_urls, discovered_container_names = discover_backend_urls(
            image_filter=container_image, prefix=container_prefix,
        )
        if container_names is None:
            container_names = discovered_container_names
        if not backend_urls:
            logger.error("No containers found. Start containers with: gma env up")
            return []

    logger.info(f"Using {len(backend_urls)} container(s): {backend_urls}")

    # Create clients
    clients = [
        GMAClient(url, device=device, step_wait_time=step_wait_time)
        for url in backend_urls
    ]
    # Build task registry
    scan_dirs = extra_task_dirs or []
    registry = TaskRegistry(*scan_dirs)

    # Determine task list
    if tasks:
        task_list = [t for t in tasks if registry.has(t)]
        missing = [t for t in tasks if not registry.has(t)]
        if missing:
            logger.warning(f"Tasks not found (skipped): {missing}")
    else:
        task_list = registry.list_names()

    # Skip already-finished tasks
    if skip_finished:
        finished = scan_finished_tasks(log_root, task_list)
        remaining = [t for t in task_list if t not in finished]
        logger.info(
            f"Tasks: {len(task_list)} total, {len(finished)} finished, {len(remaining)} remaining"
        )
    else:
        finished = {}
        remaining = list(task_list)
        logger.info(f"Tasks: {len(task_list)} total, rerunning all tasks")

    if not remaining:
        logger.info("All tasks already completed")
        return [
            TaskResult(task_name=name, score=score)
            for name, score in finished.items()
        ]

    if shuffle:
        random.shuffle(remaining)

    # Build client queue
    num_workers = min(
        max_concurrency or len(clients),
        len(clients),
        len(remaining),
    )
    client_queue: Queue = Queue(maxsize=len(clients))
    for i, c in enumerate(clients):
        if container_names and i < len(container_names):
            name = container_names[i]
        else:
            name = _default_container_name_for_url(
                backend_urls[i],
                i,
                container_prefix=container_prefix,
            )
        lease = EnvironmentLease(client=c, container_name=name)
        if robust_env_recovery:
            _initialize_environment_async(
                lease,
                client_queue,
                timeout=robust_env_recovery_timeout,
                restart=robust_env_restart,
            )
        else:
            c.init()
            client_queue.put(lease)

    # Execute tasks in parallel
    logger.info(f"Running {len(remaining)} tasks with {num_workers} worker(s)")
    results = Parallel(n_jobs=num_workers, backend="threading")(
        delayed(_process_task)(
            task_name=name,
            client_queue=client_queue,
            agent_type=agent_type,
            agent_kwargs=agent_kwargs,
            user_simulator_kwargs=user_simulator_kwargs,
            task_registry=registry,
            log_root=log_root,
            max_steps=max_steps,
            evaluate_each_step=evaluate_each_step,
            reset_task_logs=reset_task_logs,
            robust_env_recovery=robust_env_recovery,
            robust_env_max_task_retries=robust_env_max_task_retries,
            robust_env_recovery_timeout=robust_env_recovery_timeout,
            robust_env_restart=robust_env_restart,
        )
        for name in remaining
    )

    # Merge with previously finished
    all_results = [
        TaskResult(task_name=name, score=score)
        for name, score in finished.items()
    ]
    all_results.extend(results)

    # Summary
    scored = [r for r in all_results if r.score is not None]
    failed = [r for r in all_results if r.error is not None]
    if scored:
        avg = sum(r.score for r in scored) / len(scored)
        logger.info(
            f"Results: {len(scored)} scored (avg={avg:.3f}), {len(failed)} failed"
        )

    return all_results
