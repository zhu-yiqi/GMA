"""GMA command-line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from loguru import logger


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gma",
        description="GMA: General Mobile Assistant Android benchmark",
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    env_parser = sub.add_parser("env", help="Manage Docker environments")
    env_sub = env_parser.add_subparsers(dest="env_action")
    env_sub.add_parser("check", help="Check prerequisites")

    up = env_sub.add_parser("up", help="Launch containers")
    up.add_argument("--count", type=int, default=1, help="Number of containers")
    up.add_argument("--image", default="gma:latest", help="Docker image")
    up.add_argument("--interval", type=float, default=15.0, help="Seconds between launches")
    up.add_argument(
        "--no-vnc",
        dest="enable_vnc",
        action="store_false",
        default=True,
        help="Start headless containers without the browser noVNC endpoint",
    )

    env_sub.add_parser("down", help="Stop all containers")
    env_sub.add_parser("list", help="List running containers")

    reset_p = env_sub.add_parser("reset", help="Prepare a ready environment")
    reset_p.add_argument("--url", default=None, help="Container backend URL")
    reset_p.add_argument("--device", default="emulator-5554")
    reset_p.add_argument("--snapshot", default="gma_ready_state")

    clear_p = env_sub.add_parser("clear", help="Load a snapshot and clear environment drift")
    clear_p.add_argument("--url", default=None, help="Container backend URL")
    clear_p.add_argument("--device", default="emulator-5554")
    clear_p.add_argument("--snapshot", default="gma_ready_state")

    baseline_p = env_sub.add_parser(
        "save-backend-baseline",
        help="Rebuild a clean environment and save reusable backend baselines",
    )
    baseline_p.add_argument("--url", default=None, help="Container backend URL")
    baseline_p.add_argument("--device", default="emulator-5554")
    baseline_p.add_argument("--snapshot", default="gma_ready_state")

    ev = sub.add_parser("eval", help="Run evaluation")
    _add_agent_args(ev)
    ev.add_argument("--task", nargs="*", default=None, help="Specific task(s) to run")
    ev.add_argument("--max-steps", type=int, default=None, help="Max steps per task")
    ev.add_argument("--log-dir", default=None, help="Log directory")
    ev.add_argument("--step-wait", type=float, default=None, help="Wait time between steps")
    ev.add_argument("--shuffle", action="store_true", help="Randomize task order")
    ev.add_argument("--task-dir", nargs="*", default=None, help="Extra task directories")
    ev.add_argument("--config", default=None, help="Path to config TOML")
    ev.add_argument("--max-concurrency", type=int, default=None, help="Max parallel tasks")
    ev.add_argument("--no-skip-finished", action="store_true", help="Rerun finished tasks")
    ev.add_argument("--reset-task-logs", action="store_true", help="Clear each task log dir before running")
    ev.add_argument(
        "--no-evaluate-each-step",
        action="store_true",
        help="Evaluate only after the final step",
    )

    ts = sub.add_parser("test", help="Run one task for debugging")
    ts.add_argument("task", help="Task name")
    _add_agent_args(ts)
    ts.add_argument("--max-steps", type=int, default=None, help="Max steps")
    ts.add_argument("--log-dir", default=None, help="Log directory")
    ts.add_argument("--step-wait", type=float, default=None)
    ts.add_argument("--task-dir", nargs="*", default=None, help="Extra task directories")
    ts.add_argument("--config", default=None)
    ts.add_argument("--max-concurrency", type=int, default=1)
    ts.add_argument("--reset-task-logs", action="store_true")
    ts.add_argument("--no-evaluate-each-step", action="store_true")

    manual = sub.add_parser("manual", help="Initialize a task and evaluate manual phone actions")
    manual.add_argument("task", help="Task name")
    manual.add_argument("--url", default=None, help="Container backend URL")
    manual.add_argument("--device", default="emulator-5554")
    manual.add_argument("--task-dir", nargs="*", default=None, help="Extra task directories")
    manual.add_argument("--config", default=None, help="Path to config TOML")
    manual.add_argument("--agent-profile", default=None, help="Named profile used as user-simulator fallback")
    manual.add_argument("--model", default=None, help="User-simulator fallback model")
    manual.add_argument("--base-url", default=None, help="User-simulator fallback LLM base URL")
    manual.add_argument("--api-key", default=None, help="User-simulator fallback API key")

    annotate = sub.add_parser("annotate", help="Start the browser annotation server")
    annotate.add_argument("--host", default="0.0.0.0")
    annotate.add_argument("--port", type=int, default=7860)
    annotate.add_argument("--url", default=None, help="Default container backend URL")
    annotate.add_argument("--device", default="emulator-5554")
    annotate.add_argument("--task-dir", nargs="*", default=None, help="Extra task directories")
    annotate.add_argument("--token", default=None, help="Optional API token")

    generation = sub.add_parser("generate", help="Run the task-generation pipeline")
    generation.add_argument("args", nargs=argparse.REMAINDER, help="Arguments passed to task_generation.cli")

    task_parser = sub.add_parser("task", help="Task information")
    task_sub = task_parser.add_subparsers(dest="task_action")
    tl = task_sub.add_parser("list", help="List available tasks")
    tl.add_argument("--task-dir", nargs="*", default=None, help="Extra task directories")

    agent_parser = sub.add_parser("agent", help="Agent information")
    agent_sub = agent_parser.add_subparsers(dest="agent_action")
    agent_sub.add_parser("list", help="List available agents")

    logs_parser = sub.add_parser("logs", help="View evaluation logs")
    logs_sub = logs_parser.add_subparsers(dest="logs_action")
    lr = logs_sub.add_parser("results", help="Print results summary")
    lr.add_argument("--log-dir", default="logs", help="Log directory")

    sv = sub.add_parser("server", help="Start the device proxy server")
    sv.add_argument("--host", default="0.0.0.0")
    sv.add_argument("--port", type=int, default=8000)

    return parser


def _add_agent_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--agent-profile", default=None, help="Named profile in configs/default.toml")
    parser.add_argument("--agent-type", default=None, help="Agent type or path to .py file")
    parser.add_argument("--model", default=None, help="Model name")
    parser.add_argument("--base-url", default=None, help="LLM base URL")
    parser.add_argument("--api-key", default=None, help="API key")


def _resolve_agent_args(args):
    from gma.core.config import load_config, resolve_agent_config

    config = load_config(getattr(args, "config", None))
    agent_config = resolve_agent_config(config, getattr(args, "agent_profile", None))
    agent_type = getattr(args, "agent_type", None) or agent_config.type
    model = args.model if getattr(args, "model", None) is not None else agent_config.model
    base_url = args.base_url if getattr(args, "base_url", None) is not None else agent_config.base_url
    api_key = args.api_key if getattr(args, "api_key", None) is not None else agent_config.api_key
    return config, agent_type, model, base_url, api_key


def _resolve_user_simulator_kwargs(config, model: str, base_url: str, api_key: str) -> dict:
    simulator = config.user_simulator
    return {
        "model_name": simulator.model or model,
        "llm_base_url": simulator.base_url or base_url,
        "api_key": simulator.api_key or api_key,
        "temperature": simulator.temperature,
        "max_tokens": simulator.max_tokens,
        "timeout": simulator.timeout,
        "retries": simulator.retries,
    }


def _print_eval_result(result) -> None:
    status = "PASS" if result.passed else "FAIL"
    print(f"{status} score={result.score:.2f}")
    for item in result.criterion_results:
        item_status = "PASS" if item.passed else "FAIL"
        print(
            f"  [{item_status}] {item.name} "
            f"({item.score:.2f}, w={item.weight}): {item.reason}"
        )


def _manual_checkpoint(context):
    try:
        context.client.screenshot(wait=True)
    except Exception as exc:
        logger.warning(f"Manual screenshot capture failed: {exc}")
    result = context.task.evaluate(context.client)
    _print_eval_result(result)
    return result


def _print_manual_info(context) -> None:
    task = context.task
    print(f"Goal: {task.goal}")
    print(f"Apps: {', '.join(sorted(task.apps)) if task.apps else '(none)'}")
    print(f"Snapshot: {task.snapshot}")
    print(f"Assets: {len(getattr(task, 'assets', ()) or ())}")
    print(f"Container: {context.container_name or 'manual'} ({context.url})")


def _print_manual_help() -> None:
    print("Manual commands:")
    print("  enter, eval, check, status    Capture a screenshot and run evaluation")
    print("  answer <text>                 Submit a terminal answer, then evaluate")
    print("  ask <question>                Ask the task user simulator")
    print("  call_user <question>          Alias for ask")
    print("  goal                          Show the task goal")
    print("  info                          Show task and environment details")
    print("  help                          Show this help")
    print("  quit, exit                    Run one final evaluation and stop")


def _manual_ask_user(user_simulator, question: str) -> None:
    response = user_simulator.respond(question)
    info = getattr(user_simulator, "last_response_info", {}) or {}
    source = info.get("source", "unknown")
    if info.get("should_respond") is False:
        print(f"user> [no response] ({source})")
    else:
        print(f"user> {response} ({source})")


def cmd_env(args):
    from rich.console import Console
    from rich.table import Table

    from gma.runtime.docker import discover_containers, launch_containers, stop_all_containers

    console = Console()

    if args.env_action == "check":
        import shutil
        import subprocess

        docker_ok = shutil.which("docker") is not None
        console.print(f"Docker: {'[green]OK[/]' if docker_ok else '[red]NOT FOUND[/]'}")
        try:
            kvm_ok = subprocess.run(
                "test -r /dev/kvm",
                shell=True,
                capture_output=True,
            ).returncode == 0
        except Exception:
            kvm_ok = False
        console.print(f"KVM:    {'[green]OK[/]' if kvm_ok else '[yellow]NOT AVAILABLE[/]'}")
        return

    if args.env_action == "up":
        results = launch_containers(
            count=args.count,
            image=args.image,
            launch_interval=args.interval,
            enable_vnc=args.enable_vnc,
        )
        console.print(f"Launched {len(results)} container(s)")
        for result in results:
            line = f"  {result['name']} -> {result['backend_url']}"
            if result.get("vnc_url"):
                line += f"  VNC: {result['vnc_url']}"
            console.print(line)
        return

    if args.env_action == "down":
        stop_all_containers()
        console.print("All containers stopped")
        return

    if args.env_action == "list":
        containers = discover_containers()
        if not containers:
            console.print("No running containers")
            return
        table = Table(title="GMA Containers")
        table.add_column("Name")
        table.add_column("URL")
        table.add_column("VNC")
        table.add_column("Image")
        for container in containers:
            vnc = (
                f"http://localhost:{container['vnc_port']}/vnc.html"
                if container.get("vnc_port")
                else "-"
            )
            table.add_row(container["name"], container["backend_url"], vnc, container["image"])
        console.print(table)
        return

    if args.env_action in {"reset", "clear", "save-backend-baseline"}:
        from gma.runtime.client import GMAClient
        from gma.tasks.base import (
            clear_environment,
            ensure_ready_state_apps,
            load_snapshot_state_status,
            repair_loaded_snapshot_shell_state,
            reset_backend_state,
        )

        url = args.url
        if url is None:
            containers = discover_containers()
            if not containers:
                console.print("[red]No running containers found[/red]")
                return
            url = containers[0]["backend_url"]
            console.print(f"Using container: {containers[0]['name']} ({url})")

        client = GMAClient(url, device=args.device)
        client.init()

        if args.env_action == "save-backend-baseline":
            from gma.apps.backend_baseline import baseline_disabled, save_backend_baseline
            from gma.apps.elementx import ELEMENTX_BASELINE, ensure_elementx_backend
            from gma.apps.mattermost import MATTERMOST_BASELINE, ensure_mattermost_backend
            from gma.apps.offline_webapps import (
                HMDP,
                MALL,
                MEITUAN,
                XIAOSHILIU,
                ensure_offline_webapp_backend,
                offline_backend_baseline,
            )
            from gma.apps.tempus import TEMPUS_BASELINE, clear_tempus_user_state, ensure_tempus_backend
            from gma.assets.apply import (
                MASTODON_BASELINE,
                _ensure_mastodon_backend,
                clear_mastodon_app_cache,
                clear_mastodon_user_state,
            )

            with baseline_disabled():
                status = load_snapshot_state_status(client, snapshot=args.snapshot)
                ok = bool(status["ok"])
                if ok:
                    ok = clear_environment(client)
                if ok:
                    ok = ensure_ready_state_apps(
                        client,
                        snapshot=args.snapshot,
                        bootstrap_apps=True,
                    )
                if ok:
                    clear_tempus_user_state(client)
                    clear_mastodon_user_state(client)
                    clear_mastodon_app_cache(client)
            if not ok:
                console.print("[red]Failed to rebuild clean environment before saving backend baselines[/red]")
                raise SystemExit(1)

            specs = [
                (MATTERMOST_BASELINE, ensure_mattermost_backend),
                (ELEMENTX_BASELINE, ensure_elementx_backend),
                (TEMPUS_BASELINE, ensure_tempus_backend),
                (MASTODON_BASELINE, _ensure_mastodon_backend),
                (offline_backend_baseline(MALL), lambda c: ensure_offline_webapp_backend(c, MALL)),
                (offline_backend_baseline(MEITUAN), lambda c: ensure_offline_webapp_backend(c, MEITUAN)),
                (offline_backend_baseline(XIAOSHILIU), lambda c: ensure_offline_webapp_backend(c, XIAOSHILIU)),
                (offline_backend_baseline(HMDP), lambda c: ensure_offline_webapp_backend(c, HMDP)),
            ]
            for spec, prepare in specs:
                console.print(f"Preparing backend baseline: {spec.label}")
                prepare(client)
                if spec.label == "Tempus":
                    clear_tempus_user_state(client)
                console.print(f"Saving backend baseline: {spec.label}")
                save_backend_baseline(client, spec)

            if args.snapshot == "gma_ready_state":
                saved = client.save_snapshot(args.snapshot)
                if saved:
                    logger.info(f"Saved matched Android snapshot: {saved}")
                else:
                    console.print(f"[red]Failed to save Android snapshot {args.snapshot}[/red]")
                    raise SystemExit(1)
            console.print("[green]Saved backend baselines[/green]")
            return

        status = load_snapshot_state_status(client, snapshot=args.snapshot)
        ok = bool(status["ok"])

        if ok and args.env_action == "clear":
            ok = clear_environment(client)
            if ok and args.snapshot == "gma_ready_state":
                ok = ensure_ready_state_apps(client, snapshot=args.snapshot, bootstrap_apps=True)
            console.print(
                f"[green]Environment cleared from snapshot {args.snapshot}[/green]"
                if ok else f"[red]Environment clear failed for snapshot {args.snapshot}[/red]"
            )
            if not ok:
                raise SystemExit(1)
            return

        if ok and status.get("loaded_snapshot"):
            # Loading an emulator snapshot only restores Android disk state.
            # App backends run outside the emulator snapshot and can retain
            # asset-smoke/task drift. Restore backend baselines only; do not
            # clear Android app data on normal reset. Run the loaded-snapshot
            # session repair path afterwards so WebView/PWA apps get their
            # local login state refreshed against the restored backends.
            ok = reset_backend_state(client)
            if ok:
                ok = ensure_ready_state_apps(client, snapshot=args.snapshot, bootstrap_apps=False)
            if ok and args.snapshot == "gma_ready_state":
                saved = client.save_snapshot(args.snapshot)
                if saved:
                    logger.info(f"Saved repaired Android snapshot: {saved}")
                else:
                    console.print(f"[red]Failed to save Android snapshot {args.snapshot}[/red]")
                    raise SystemExit(1)
            message = (
                f"Environment loaded snapshot {args.snapshot}"
                if ok
                else f"Failed to reset backend state for snapshot {args.snapshot}"
            )
        elif ok:
            ok = clear_environment(client)
            if ok:
                ok = ensure_ready_state_apps(client, snapshot=args.snapshot, bootstrap_apps=True)
            if ok and args.snapshot == "gma_ready_state":
                saved = client.save_snapshot(args.snapshot)
                if saved:
                    logger.info(f"Saved rebuilt snapshot: {saved}")
            message = f"Environment rebuilt snapshot {args.snapshot}"
        else:
            message = f"Failed to load snapshot {args.snapshot}"

        console.print(f"[green]{message}[/green]" if ok else f"[red]{message}[/red]")
        if not ok:
            raise SystemExit(1)
        return

    console.print("Usage: gma env {check|up|down|list|reset|clear}")


def cmd_eval(args):
    from rich.console import Console
    from rich.table import Table

    from gma.core.runner import run_evaluation

    console = Console()
    config, agent_type, model, base_url, api_key = _resolve_agent_args(args)
    max_steps = args.max_steps if args.max_steps is not None else config.runtime.max_steps
    log_dir = args.log_dir or config.evaluation.log_dir
    step_wait = args.step_wait if args.step_wait is not None else config.runtime.step_wait_time

    results = run_evaluation(
        agent_type=agent_type,
        agent_kwargs={"model_name": model, "llm_base_url": base_url, "api_key": api_key},
        user_simulator_kwargs=_resolve_user_simulator_kwargs(config, model, base_url, api_key),
        log_root=log_dir,
        tasks=args.task,
        max_steps=max_steps,
        step_wait_time=step_wait,
        shuffle=args.shuffle,
        extra_task_dirs=args.task_dir,
        device=config.runtime.device,
        container_image=config.runtime.container_image,
        container_prefix=config.runtime.container_prefix,
        max_concurrency=args.max_concurrency,
        skip_finished=not args.no_skip_finished,
        reset_task_logs=args.reset_task_logs,
        evaluate_each_step=not args.no_evaluate_each_step,
    )

    table = Table(title="Evaluation Results")
    table.add_column("Task")
    table.add_column("Score", justify="right")
    table.add_column("Steps", justify="right")
    table.add_column("Status")
    for result in sorted(results, key=lambda item: item.task_name):
        if result.error:
            table.add_row(result.task_name, "-", "-", f"[red]ERROR: {result.error[:80]}[/]")
        else:
            score = f"{result.score:.2f}" if result.score is not None else "-"
            color = "green" if result.success else "red"
            table.add_row(
                result.task_name,
                score,
                str(result.steps),
                f"[{color}]{'PASS' if result.success else 'FAIL'}[/]",
            )
    console.print(table)

    scored = [item for item in results if item.score is not None]
    if scored:
        avg = sum(item.score for item in scored) / len(scored)
        console.print(f"\nAverage score: {avg:.3f} ({len(scored)} tasks)")


def cmd_test(args):
    args.task = [args.task]
    args.shuffle = False
    args.no_skip_finished = True
    cmd_eval(args)


def cmd_manual(args):
    from gma.agents.user_simulator import UserSimulator
    from gma.core.task_runtime import attach_task
    from gma.runtime.models import Action

    config, _agent_type, model, base_url, api_key = _resolve_agent_args(args)
    user_simulator_kwargs = _resolve_user_simulator_kwargs(config, model, base_url, api_key)

    context = attach_task(
        args.task,
        url=args.url,
        device=args.device,
        extra_task_dirs=args.task_dir,
    )
    if context is None:
        print("No running GMA containers found")
        return

    if not context.task.initialize(context.client):
        print(f"Task initialization failed for {context.task.name}")
        return
    user_simulator = UserSimulator.from_task(context.task, **user_simulator_kwargs)

    print(f"Initialized task {context.task.name}")
    _print_manual_info(context)
    _manual_checkpoint(context)
    _print_manual_help()

    try:
        while True:
            try:
                raw_command = input("manual> ").strip()
            except EOFError:
                raw_command = "quit"

            command = raw_command.lower()
            if command in {"", "enter", "eval", "check", "status"}:
                _manual_checkpoint(context)
            elif command == "answer":
                answer_text = input("answer text> ")
                context.client.step(Action(action_type="answer", text=answer_text))
                _manual_checkpoint(context)
            elif command.startswith("answer "):
                answer_text = raw_command[len("answer "):]
                context.client.step(Action(action_type="answer", text=answer_text))
                _manual_checkpoint(context)
            elif command in {"ask", "call_user"}:
                question = input("question> ")
                _manual_ask_user(user_simulator, question)
            elif command.startswith("ask "):
                _manual_ask_user(user_simulator, raw_command[len("ask "):])
            elif command.startswith("call_user "):
                _manual_ask_user(user_simulator, raw_command[len("call_user "):])
            elif command == "goal":
                print(context.task.goal)
            elif command == "info":
                _print_manual_info(context)
            elif command == "help":
                _print_manual_help()
            elif command in {"quit", "exit"}:
                _manual_checkpoint(context)
                break
            else:
                print(f"Unknown command: {command}")
                _print_manual_help()
    finally:
        context.task.finalize(context.client)


def cmd_annotate(args):
    from gma.annotator.server import start_server

    start_server(
        host=args.host,
        port=args.port,
        default_url=args.url,
        default_device=args.device,
        task_dirs=args.task_dir,
        token=args.token,
    )


def cmd_generate(args):
    import task_generation.cli as generation_cli

    old_argv = sys.argv
    try:
        sys.argv = ["gma generate", *args.args]
        generation_cli.main()
    finally:
        sys.argv = old_argv


def cmd_task_list(args):
    from rich.console import Console
    from rich.table import Table

    from gma.tasks.registry import TaskRegistry

    console = Console()
    registry = TaskRegistry(*(args.task_dir or []))
    tasks = registry.list_tasks()
    if not tasks:
        console.print("No tasks found")
        return

    table = Table(title=f"Available Tasks ({len(tasks)})")
    table.add_column("Name")
    table.add_column("Apps")
    table.add_column("Tags")
    table.add_column("Goal", max_width=60)
    for task in sorted(tasks, key=lambda item: item["name"]):
        table.add_row(
            task["name"],
            ", ".join(task["apps"]),
            ", ".join(task["tags"]),
            task["goal"],
        )
    console.print(table)


def cmd_agent_list(args):
    from rich.console import Console

    from gma.agents.registry import list_agents

    console = Console()
    agents = list_agents()
    if not agents:
        console.print("No registered agents")
        return
    console.print("Registered agents:")
    for agent in agents:
        console.print(f"  - {agent}")


def cmd_logs_results(args):
    from rich.console import Console
    from rich.table import Table

    from gma.logging.trajectory import scan_finished_tasks

    console = Console()
    finished = scan_finished_tasks(args.log_dir)
    if not finished:
        console.print(f"No results found in {args.log_dir}")
        return

    table = Table(title=f"Results ({len(finished)} tasks)")
    table.add_column("Task")
    table.add_column("Score", justify="right")
    table.add_column("Status")
    for name, score in sorted(finished.items()):
        color = "green" if score > 0 else "red"
        table.add_row(name, f"{score:.2f}", f"[{color}]{'PASS' if score > 0 else 'FAIL'}[/]")
    console.print(table)
    avg = sum(finished.values()) / len(finished)
    console.print(f"\nAverage: {avg:.3f}")


def cmd_server(args):
    from gma.core.server import start_server

    start_server(host=args.host, port=args.port)


def main():
    parser = create_parser()
    args = parser.parse_args()

    try:
        if args.command == "env":
            cmd_env(args)
        elif args.command == "eval":
            cmd_eval(args)
        elif args.command == "test":
            cmd_test(args)
        elif args.command == "manual":
            cmd_manual(args)
        elif args.command == "annotate":
            cmd_annotate(args)
        elif args.command == "generate":
            cmd_generate(args)
        elif args.command == "task":
            if args.task_action == "list":
                cmd_task_list(args)
            else:
                parser.parse_args(["task", "--help"])
        elif args.command == "agent":
            if args.agent_action == "list":
                cmd_agent_list(args)
            else:
                parser.parse_args(["agent", "--help"])
        elif args.command == "logs":
            if args.logs_action == "results":
                cmd_logs_results(args)
            else:
                parser.parse_args(["logs", "--help"])
        elif args.command == "server":
            cmd_server(args)
        else:
            parser.print_help()
            sys.exit(1)
    except KeyboardInterrupt:
        print()
        sys.exit(130)


if __name__ == "__main__":
    main()
