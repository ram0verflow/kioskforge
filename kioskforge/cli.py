from __future__ import annotations

from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from kioskforge import __version__
from kioskforge.config import ConfigError, config_summary, load_config
from kioskforge.generator import generate_overlay, inject_boot_partition

app = typer.Typer(
    name="kioskforge",
    help="Declarative Raspberry Pi kiosk provisioning from a YAML config.",
    no_args_is_help=True,
)
console = Console()


def _load(path: Path):
    try:
        return load_config(path)
    except ConfigError as exc:
        console.print(f"[red]Config error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    except yaml.YAMLError as exc:
        console.print(f"[red]YAML error:[/red] {exc}")
        raise typer.Exit(code=1) from exc


@app.callback()
def main() -> None:
    """Kioskforge CLI."""


@app.command("version")
def version_cmd() -> None:
    console.print(f"kioskforge {__version__}")


@app.command()
def validate(config: Path = typer.Argument(..., help="Path to kioskforge.yaml")) -> None:
    cfg = _load(config)
    console.print("[green]Valid[/green]")
    console.print(yaml.safe_dump(config_summary(cfg), sort_keys=False))


@app.command()
def plan(config: Path = typer.Argument(..., help="Path to kioskforge.yaml")) -> None:
    cfg = _load(config)
    table = Table(title="Kioskforge plan")
    table.add_column("Setting", style="cyan")
    table.add_column("Value")
    for key, value in config_summary(cfg).items():
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value) or "—"
        table.add_row(key, str(value))
    console.print(table)
    console.print(
        Panel(
            "[bold]Recommended workflow[/bold]\n"
            "1. Flash Raspberry Pi OS (64-bit) with [cyan]Raspberry Pi Imager[/cyan].\n"
            "2. Mount the [cyan]bootfs[/cyan] partition.\n"
            "3. Run [cyan]kioskforge inject[/cyan] — writes overlay + firstrun hook.\n"
            "4. Boot once; provisioning runs automatically.",
            title="Post-flash provisioning",
        )
    )


@app.command()
def generate(
    config: Path = typer.Argument(..., help="Path to kioskforge.yaml"),
    output: Path = typer.Option(Path("./kioskforge-out"), "--output", "-o"),
    compose: Path | None = typer.Option(None, "--compose", help="docker-compose.yml to bundle"),
) -> None:
    cfg = _load(config)
    overlay = generate_overlay(cfg, output, compose_source=compose)
    console.print(f"[green]Generated[/green] overlay at {overlay}")


@app.command()
def inject(
    config: Path = typer.Argument(..., help="Path to kioskforge.yaml"),
    boot_mount: Path = typer.Option(..., "--boot-mount", "-b", help="Mounted boot partition"),
    compose: Path | None = typer.Option(None, "--compose", help="docker-compose.yml to bundle"),
) -> None:
    cfg = _load(config)
    try:
        target = inject_boot_partition(cfg, boot_mount, compose_source=compose)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc
    console.print(f"[green]Injected[/green] overlay at {target}")
    console.print("Eject SD card, boot Pi, then: journalctl -u kioskforge-firstboot -f")


if __name__ == "__main__":
    app()
