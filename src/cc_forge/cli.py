"""CLI entry point for CC Forge."""

from __future__ import annotations

import click

from cc_forge import __version__


@click.group(invoke_without_command=True)
@click.version_option(__version__, prog_name="forge")
@click.option("--gpu", is_flag=True, help="Use Vulkan GPU Ollama service instead of CPU.")
@click.pass_context
def main(ctx: click.Context, gpu: bool) -> None:
    """CC Forge — Local-first AI development forge.

    Run `forge` with no arguments to start an interactive agent session
    in the current git repository.
    """
    ctx.ensure_object(dict)
    ctx.obj["gpu"] = gpu
    if ctx.invoked_subcommand is None:
        ctx.invoke(run, gpu=gpu)


@main.command()
@click.option("--repo", default=".", help="Path to git repository (default: current directory).")
@click.option("--agent", default="claude", type=click.Choice(["claude", "aider"]),
              help="Agent to use inside the container.")
@click.option("--gpu", is_flag=True, help="Use Vulkan GPU Ollama service instead of CPU.")
def run(repo: str, agent: str, gpu: bool) -> None:
    """Start an interactive agent session."""
    from cc_forge.config import load_config
    from cc_forge.session import start_session

    cfg = load_config()
    start_session(cfg, repo_path=repo, agent=agent, use_gpu=gpu)


@main.command()
def status() -> None:
    """Show running forge sessions."""
    from cc_forge.docker import list_forge_containers

    containers = list_forge_containers()
    if not containers:
        click.echo("No running forge sessions.")
        return
    for c in containers:
        click.echo(f"  {c['name']}  {c['status']}  ({c['repo']})")


@main.command()
@click.option("--all", "stop_all", is_flag=True, help="Stop all forge sessions.")
@click.argument("name", required=False)
def stop(name: str | None, stop_all: bool) -> None:
    """Stop forge sessions."""
    from cc_forge.docker import list_forge_containers, stop_container

    containers = list_forge_containers()
    if not containers:
        click.echo("No running forge sessions.")
        return

    if stop_all:
        for c in containers:
            stop_container(c["id"])
            click.echo(f"Stopped {c['name']}")
        return

    if name is None:
        click.echo("Specify a container name or use --all.")
        return

    for c in containers:
        if c["name"] == name or c["id"].startswith(name):
            stop_container(c["id"])
            click.echo(f"Stopped {c['name']}")
            return

    click.echo(f"No forge session matching '{name}'.")
