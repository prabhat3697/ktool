from __future__ import annotations

import re
import subprocess
import sys
from typing import Optional, Any, List, Tuple

import typer
from rich.console import Console
from rich.table import Table

from .config import load_config
from .kube import get_pods_json

# Allow us to accept arbitrary arg order and parse ourselves
app = typer.Typer(
    add_completion=False,
    help="kubectl shortcuts + search + summaries",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    no_args_is_help=False,
)
ctx_app = typer.Typer(add_completion=False, help="Context shortcuts (like kubectx)")

console = Console()


def resolve_namespace(ns: Optional[str]) -> str:
    cfg = load_config()
    return ns or cfg.default_namespace


def resolve_service(tag: Optional[str]) -> Optional[str]:
    if not tag:
        return None
    cfg = load_config()
    return cfg.services.get(tag, tag)


def pod_state(pod: dict[str, Any]) -> tuple[str, bool]:
    status = pod.get("status", {})
    phase = status.get("phase", "Unknown")

    for cs in status.get("containerStatuses", []) or []:
        state = cs.get("state", {}) or {}
        waiting = state.get("waiting")
        terminated = state.get("terminated")
        if waiting:
            return waiting.get("reason", "Waiting"), True
        if terminated:
            code = terminated.get("exitCode", 0)
            if code != 0:
                return f"{terminated.get('reason','Exit')}(exit={code})", True

    bad = phase not in ("Running", "Succeeded")
    return phase, bad


def pods_impl(
        service: Optional[str],
        namespace: Optional[str],
        search: Optional[str],
        summary: bool,
        bad_only: bool,
        show_command: bool,
):
    ns = resolve_namespace(namespace)
    svc = resolve_service(service)

    # Show the actual kubectl command if requested
    if show_command:
        cmd = ["kubectl", "get", "pods", "-n", ns, "-o", "json"]
        console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")

    data = get_pods_json(ns)
    items = data.get("items", []) or []

    filtered = []
    for pod in items:
        name = pod["metadata"]["name"]
        if svc and svc not in name:
            continue
        if search and not re.search(search, name):
            continue
        filtered.append(pod)

    if not filtered:
        console.print("[yellow]No pods matched[/yellow]")
        raise typer.Exit(1)

    table = Table(title=f"Pods in {ns}")
    table.add_column("Pod")
    table.add_column("State")
    table.add_column("Bad")

    counts: dict[str, int] = {}
    bad_pods = []

    for pod in filtered:
        state, bad = pod_state(pod)
        counts[state] = counts.get(state, 0) + 1
        if bad:
            bad_pods.append(pod)

    show = bad_pods if bad_only else filtered
    for pod in show:
        name = pod["metadata"]["name"]
        state, bad = pod_state(pod)
        table.add_row(name, state, "YES" if bad else "")

    console.print(table)

    if summary:
        console.print(
            "[bold]Summary:[/bold] "
            + ", ".join(f"{k}={v}" for k, v in counts.items())
        )
        console.print(
            f"[bold]Total:[/bold] {len(filtered)}  "
            f"[bold]Problematic:[/bold] {len(bad_pods)}"
        )


def parse_args(argv: List[str]) -> Tuple[Optional[str], Optional[str], Optional[str], bool, bool, bool]:
    """
    Accepts both:
      k oss-primary --summary
      k pods oss-primary --summary
    And allows options anywhere.
    """
    # Strip optional leading "pods"
    args = argv[:]
    if args and args[0] == "pods":
        args = args[1:]

    service: Optional[str] = None
    namespace: Optional[str] = None
    search: Optional[str] = None
    summary = False
    bad_only = False
    show_command = False

    i = 0
    while i < len(args):
        a = args[i]

        if a in ("--summary",):
            summary = True
            i += 1
            continue

        if a in ("--bad",):
            bad_only = True
            i += 1
            continue

        if a in ("--show-command", "--showCommand"):
            show_command = True
            i += 1
            continue

        if a in ("-n", "--ns"):
            if i + 1 >= len(args):
                raise typer.BadParameter("Missing value after -n/--ns")
            namespace = args[i + 1]
            i += 2
            continue

        if a in ("-s", "--search"):
            if i + 1 >= len(args):
                raise typer.BadParameter("Missing value after -s/--search")
            search = args[i + 1]
            i += 2
            continue

        # First non-flag token becomes service (oss-primary etc.)
        if not a.startswith("-") and service is None:
            service = a
            i += 1
            continue

        # Ignore anything unknown for now
        i += 1

    return service, namespace, search, summary, bad_only, show_command


def _main_impl(args: List[str]):
    """Internal implementation that parses args and calls pods_impl"""
    service, namespace, search, summary, bad_only, show_command = parse_args(args)
    pods_impl(service, namespace, search, summary, bad_only, show_command)


@app.command("pods", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def pods_cmd(ctx: typer.Context):
    """List pods (can be called as 'k pods' or just 'k')"""
    # For the pods command, use ctx.args (everything after 'pods')
    # But we need to handle the case where 'pods' itself is in sys.argv
    # So we'll use sys.argv and strip 'pods' if it's the first arg
    args = sys.argv[1:] if len(sys.argv) > 1 else []
    if args and args[0] == "pods":
        args = args[1:]
    _main_impl(args)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    List pods. Usage examples:
      k oss-primary --summary
      k pods oss-primary --summary
      k --search pattern
    """
    # Always use sys.argv to bypass Typer's command matching
    # Skip the first argument (command name 'k')
    args = sys.argv[1:] if len(sys.argv) > 1 else []
    _main_impl(args)


@ctx_app.command("use")
def use_ctx(
    region: str = typer.Argument(..., help="Alias like us-west-2"),
    show_command: bool = typer.Option(False, "--show-command", "--showCommand", help="Show the actual kubectl command"),
):
    cfg = load_config()
    real_ctx = cfg.contexts.get(region, region)
    cmd = ["kubectl", "config", "use-context", real_ctx]
    if show_command:
        console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")
    subprocess.run(cmd, check=False)


@ctx_app.command("show")
def show_ctx(
    show_command: bool = typer.Option(False, "--show-command", "--showCommand", help="Show the actual kubectl command"),
):
    cmd = ["kubectl", "config", "current-context"]
    if show_command:
        console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")
    subprocess.run(cmd, check=False)


# Wrapper function to handle arguments before Typer parses them
def main_wrapper():
    """
    Entry point wrapper that intercepts sys.argv before Typer sees it.
    This allows us to handle both 'k oss-primary --summary' and 'k pods oss-primary --summary'
    without Typer trying to match 'oss-primary' or 'pods' as commands.
    """
    # Always parse arguments directly and call the implementation
    # This bypasses Typer's command matching which would error on unknown commands
    args = sys.argv[1:] if len(sys.argv) > 1 else []
    _main_impl(args)
