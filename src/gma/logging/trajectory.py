"""Structured trajectory logger.

Saves per-task execution logs: screenshots, agent actions, evaluation
snapshots, user-simulator exchanges, and final scores. Each task gets its own
directory under the log root.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
import shutil
from datetime import datetime
from typing import Any

from loguru import logger
from PIL import Image

SCORE_FILE = "score.txt"
AGENT_TRAJECTORY_FILE = "agent_trajectory.jsonl"
EVALUATION_TRAJECTORY_FILE = "evaluation_trajectory.jsonl"
USER_SIMULATOR_FILE = "user_simulator.jsonl"
LEGACY_TRAJECTORY_FILE = "trajectory.jsonl"
SCREENSHOTS_DIR = "screenshots"


def create_run_dir(log_root: str | Path) -> Path:
    """Create a timestamped run directory under the given log root."""
    base = Path(log_root)
    base.mkdir(parents=True, exist_ok=True)
    stem = datetime.now().strftime("%Y%m%d_%H%M%S")
    candidate = base / stem
    suffix = 1
    while candidate.exists():
        candidate = base / f"{stem}_{suffix:02d}"
        suffix += 1
    candidate.mkdir(parents=True, exist_ok=False)
    return candidate


def resolve_results_dir(log_root: str | Path) -> Path:
    """Resolve a result root for reading.

    If `log_root` directly contains task folders with score files, use it.
    Otherwise, if it contains timestamped run folders, return the most recent one.
    """
    base = Path(log_root)
    if not base.exists():
        return base

    direct_score_dirs = [
        child for child in base.iterdir()
        if child.is_dir() and (child / SCORE_FILE).exists()
    ]
    if direct_score_dirs:
        return base

    run_dirs = [child for child in base.iterdir() if child.is_dir()]
    if not run_dirs:
        return base
    return sorted(run_dirs)[-1]


class TrajectoryLogger:
    """Logs task execution trajectories to disk."""

    def __init__(self, log_root: str, task_name: str):
        self.task_dir = Path(log_root) / task_name
        self.task_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir = self.task_dir / SCREENSHOTS_DIR
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self._step = 0
        self._start_time = time.time()

    def log_step(
        self,
        step: int,
        observation: Any,
        action: dict,
        response: str | None = None,
        agent_stats: dict | None = None,
    ) -> None:
        """Log a single agent step."""
        self._step = step

        screenshot_path: str | None = None
        if observation is not None and hasattr(observation, "screenshot"):
            screenshot = observation.screenshot
            if isinstance(screenshot, Image.Image):
                img_path = self.screenshots_dir / f"step_{step:03d}.png"
                screenshot.save(str(img_path))
                screenshot_path = str(img_path.relative_to(self.task_dir))

        entry = {
            "kind": "step",
            "step": step,
            "timestamp": time.time(),
            "screenshot": screenshot_path,
            "action": action,
            "response": response,
            "agent_stats": agent_stats,
        }
        with open(self.task_dir / AGENT_TRAJECTORY_FILE, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def log_evaluation(
        self,
        step: int,
        score: float,
        passed: bool,
        summary: str,
        criterion_results: list[dict] | None = None,
        phase: str = "post_step",
    ) -> None:
        """Append an evaluation snapshot for the current task state."""
        entry = {
            "kind": "evaluation",
            "step": step,
            "phase": phase,
            "timestamp": time.time(),
            "score": score,
            "passed": passed,
            "summary": summary,
            "criteria": criterion_results or [],
        }
        with open(self.task_dir / EVALUATION_TRAJECTORY_FILE, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def log_user_simulator(
        self,
        step: int,
        question: str,
        response: str,
        response_info: dict | None = None,
    ) -> None:
        """Append a simulated-user exchange triggered by a call_user action."""
        response_info = response_info or {}
        entry = {
            "kind": "user_simulator",
            "step": step,
            "timestamp": time.time(),
            "question": question,
            "response": response,
            "source": response_info.get("source"),
            "should_respond": response_info.get("should_respond"),
            "reason": response_info.get("reason"),
            "raw": response_info,
        }
        with open(self.task_dir / USER_SIMULATOR_FILE, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def log_score(self, score: float, reason: str = "") -> None:
        """Write the final score."""
        with open(self.task_dir / SCORE_FILE, "w") as f:
            f.write(f"score: {score}\n")
            if reason:
                f.write(f"{reason}\n")
        duration = time.time() - self._start_time
        logger.info(
            f"Task scored {score:.2f} in {self._step} steps ({duration:.1f}s): {reason}"
        )

    def log_metadata(self, metadata: dict) -> None:
        """Write arbitrary metadata (task goal, agent config, etc.)."""
        with open(self.task_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    def reset(self) -> None:
        """Clear trajectory data (for retries)."""
        for filename in (
            AGENT_TRAJECTORY_FILE,
            EVALUATION_TRAJECTORY_FILE,
            USER_SIMULATOR_FILE,
            LEGACY_TRAJECTORY_FILE,
        ):
            path = self.task_dir / filename
            if path.exists():
                path.unlink()

        if self.screenshots_dir.exists():
            shutil.rmtree(self.screenshots_dir)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

        for legacy_screenshot in self.task_dir.glob("step_*.png"):
            legacy_screenshot.unlink()

        self._step = 0
        self._start_time = time.time()

    def reset_task_dir(self) -> None:
        """Remove all existing task logs so a rerun starts cleanly."""
        if self.task_dir.exists():
            shutil.rmtree(self.task_dir)
        self.task_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir = self.task_dir / SCREENSHOTS_DIR
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self._step = 0
        self._start_time = time.time()


def scan_finished_tasks(log_root: str, task_names: list[str] | None = None) -> dict[str, float]:
    """Scan log directory for already-completed tasks.

    Returns a dict of task_name -> score for tasks that have a score file.
    """
    log_path = resolve_results_dir(log_root)
    if not log_path.exists():
        return {}

    finished = {}
    for d in log_path.iterdir():
        if not d.is_dir():
            continue
        if task_names is not None and d.name not in task_names:
            continue
        score_file = d / SCORE_FILE
        if score_file.exists():
            try:
                text = score_file.read_text()
                first_line = text.strip().splitlines()[0]
                score = float(first_line.split("score:")[1].strip())
                finished[d.name] = score
            except (ValueError, IndexError):
                pass
    return finished
