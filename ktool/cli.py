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


def find_pod_by_service(service: Optional[str], namespace: str, search: Optional[str] = None) -> Optional[str]:
    """Find a pod name matching the service or search pattern"""
    if not service and not search:
        return None
    
    svc = resolve_service(service)
    data = get_pods_json(namespace)
    items = data.get("items", []) or []
    
    for pod in items:
        name = pod["metadata"]["name"]
        if svc and svc in name:
            if not search or re.search(search, name):
                return name
        if search and re.search(search, name):
            return name
    
    return None


@app.command("logs", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def logs_cmd(
    ctx: typer.Context,
    pod_or_service: Optional[str] = typer.Argument(None, help="Pod name or service name"),
    namespace: Optional[str] = typer.Option(None, "-n", "--ns", help="Namespace"),
    container: Optional[str] = typer.Option(None, "-c", "--container", help="Container name"),
    follow: bool = typer.Option(False, "-f", "--follow", help="Follow log output"),
    tail: Optional[int] = typer.Option(None, "--tail", help="Number of lines to show from the end"),
    previous: bool = typer.Option(False, "-p", "--previous", help="Previous instance logs"),
    show_command: bool = typer.Option(False, "--show-command", "--showCommand", help="Show the actual kubectl command"),
):
    """Get logs from a pod"""
    ns = resolve_namespace(namespace)
    
    # If no pod specified, try to find one by service
    pod_name = pod_or_service
    if pod_or_service:
        # Check if it's a service tag first
        found_pod = find_pod_by_service(pod_or_service, ns)
        if found_pod:
            pod_name = found_pod
        # Otherwise use it as pod name directly
    
    if not pod_name:
        console.print("[red]Error: Pod name or service required[/red]")
        raise typer.Exit(1)
    
    cmd = ["kubectl", "logs", pod_name, "-n", ns]
    if container:
        cmd.extend(["-c", container])
    if follow:
        cmd.append("-f")
    if tail:
        cmd.extend(["--tail", str(tail)])
    if previous:
        cmd.append("-p")
    
    # Add any extra args passed
    if ctx.args:
        cmd.extend(ctx.args)
    
    if show_command:
        console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")
    
    subprocess.run(cmd, check=False)


@app.command("describe", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def describe_cmd(
    ctx: typer.Context,
    resource: str = typer.Argument(..., help="Resource type and name (e.g., pod/my-pod, deployment/my-deploy)"),
    namespace: Optional[str] = typer.Option(None, "-n", "--ns", help="Namespace"),
    show_command: bool = typer.Option(False, "--show-command", "--showCommand", help="Show the actual kubectl command"),
):
    """Describe a resource"""
    ns = resolve_namespace(namespace)
    
    cmd = ["kubectl", "describe", resource, "-n", ns]
    
    # Add any extra args passed
    if ctx.args:
        cmd.extend(ctx.args)
    
    if show_command:
        console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")
    
    subprocess.run(cmd, check=False)


@app.command("exec", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def exec_cmd(
    ctx: typer.Context,
    pod_or_service: str = typer.Argument(..., help="Pod name or service name"),
    namespace: Optional[str] = typer.Option(None, "-n", "--ns", help="Namespace"),
    container: Optional[str] = typer.Option(None, "-c", "--container", help="Container name"),
    stdin: bool = typer.Option(False, "-i", "--stdin", help="Keep stdin open"),
    tty: bool = typer.Option(False, "-t", "--tty", help="Allocate a TTY"),
    show_command: bool = typer.Option(False, "--show-command", "--showCommand", help="Show the actual kubectl command"),
):
    """Execute a command in a pod"""
    ns = resolve_namespace(namespace)
    
    # Try to find pod by service if it looks like a service name
    pod_name = pod_or_service
    found_pod = find_pod_by_service(pod_or_service, ns)
    if found_pod:
        pod_name = found_pod
    
    cmd = ["kubectl", "exec", pod_name, "-n", ns]
    if container:
        cmd.extend(["-c", container])
    if stdin:
        cmd.append("-i")
    if tty:
        cmd.append("-t")
    
    # Add any extra args (command to execute)
    if ctx.args:
        cmd.extend(ctx.args)
    else:
        # Default to shell if no command provided
        cmd.extend(["--", "/bin/sh"])
    
    if show_command:
        console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")
    
    subprocess.run(cmd, check=False)


@app.command("port-forward", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def port_forward_cmd(
    ctx: typer.Context,
    resource: str = typer.Argument(..., help="Resource (pod/my-pod or service/my-svc)"),
    ports: str = typer.Argument(..., help="Port mapping (e.g., 8080:80 or 8080)"),
    namespace: Optional[str] = typer.Option(None, "-n", "--ns", help="Namespace"),
    show_command: bool = typer.Option(False, "--show-command", "--showCommand", help="Show the actual kubectl command"),
):
    """Forward one or more local ports to a pod or service"""
    ns = resolve_namespace(namespace)
    
    cmd = ["kubectl", "port-forward", resource, ports, "-n", ns]
    
    # Add any extra args passed
    if ctx.args:
        cmd.extend(ctx.args)
    
    if show_command:
        console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")
    
    subprocess.run(cmd, check=False)


@app.command("get", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def get_cmd(
    ctx: typer.Context,
    resource: str = typer.Argument(..., help="Resource type (e.g., pods, services, deployments)"),
    name: Optional[str] = typer.Argument(None, help="Resource name (optional)"),
    namespace: Optional[str] = typer.Option(None, "-n", "--ns", help="Namespace"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="Output format"),
    show_command: bool = typer.Option(False, "--show-command", "--showCommand", help="Show the actual kubectl command"),
):
    """Get resources"""
    ns = resolve_namespace(namespace)
    
    cmd = ["kubectl", "get", resource, "-n", ns]
    if name:
        cmd.append(name)
    if output:
        cmd.extend(["-o", output])
    
    # Add any extra args passed
    if ctx.args:
        cmd.extend(ctx.args)
    
    if show_command:
        console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")
    
    subprocess.run(cmd, check=False)


@app.command("delete", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def delete_cmd(
    ctx: typer.Context,
    resource: str = typer.Argument(..., help="Resource type and name (e.g., pod/my-pod)"),
    namespace: Optional[str] = typer.Option(None, "-n", "--ns", help="Namespace"),
    force: bool = typer.Option(False, "--force", help="Force deletion"),
    grace_period: Optional[int] = typer.Option(None, "--grace-period", help="Grace period in seconds"),
    show_command: bool = typer.Option(False, "--show-command", "--showCommand", help="Show the actual kubectl command"),
):
    """Delete a resource"""
    ns = resolve_namespace(namespace)
    
    cmd = ["kubectl", "delete", resource, "-n", ns]
    if force:
        cmd.append("--force")
    if grace_period is not None:
        cmd.extend(["--grace-period", str(grace_period)])
    
    # Add any extra args passed
    if ctx.args:
        cmd.extend(ctx.args)
    
    if show_command:
        console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")
    
    subprocess.run(cmd, check=False)


@app.command("top", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def top_cmd(
    ctx: typer.Context,
    resource: str = typer.Argument("pods", help="Resource type (pods or nodes)"),
    name: Optional[str] = typer.Argument(None, help="Resource name (optional)"),
    namespace: Optional[str] = typer.Option(None, "-n", "--ns", help="Namespace"),
    show_command: bool = typer.Option(False, "--show-command", "--showCommand", help="Show the actual kubectl command"),
):
    """Display resource usage (CPU/memory)"""
    ns = resolve_namespace(namespace)
    
    cmd = ["kubectl", "top", resource]
    if resource == "pods":
        cmd.extend(["-n", ns])
    if name:
        cmd.append(name)
    
    # Add any extra args passed
    if ctx.args:
        cmd.extend(ctx.args)
    
    if show_command:
        console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")
    
    subprocess.run(cmd, check=False)


@app.command("rollout", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def rollout_cmd(
    ctx: typer.Context,
    action: str = typer.Argument(..., help="Rollout action (restart, status, history, undo, pause, resume)"),
    resource: str = typer.Argument(..., help="Resource (e.g., deployment/my-deploy)"),
    namespace: Optional[str] = typer.Option(None, "-n", "--ns", help="Namespace"),
    revision: Optional[int] = typer.Option(None, "--revision", help="Revision number (for history/undo)"),
    show_command: bool = typer.Option(False, "--show-command", "--showCommand", help="Show the actual kubectl command"),
):
    """Manage rollouts"""
    ns = resolve_namespace(namespace)
    
    cmd = ["kubectl", "rollout", action, resource, "-n", ns]
    if revision is not None:
        cmd.extend(["--revision", str(revision)])
    
    # Add any extra args passed
    if ctx.args:
        cmd.extend(ctx.args)
    
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
