"""Stellar Pipeline CLI — Learn dbt through a sci-fi narrative."""
from __future__ import annotations

import typer
from rich.console import Console

from stellar_dbt.engine.game_engine import GameEngine
from stellar_dbt.engine.state_manager import load_state, save_state
from stellar_dbt.levels.loader import load_level, list_levels
from stellar_dbt.ui import terminal_ui as ui

app = typer.Typer(
    name="stellar",
    help="Learn dbt through a sci-fi narrative. Powered by real dbt + DuckDB.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def start(level: int = typer.Argument(1, help="Level number to start")):
    """Initialize a level and begin the mission."""
    ui.render_header()
    try:
        report = GameEngine.start_level(level)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    state = load_state()
    level_config = load_level(state.current_level)
    ui.render_status(state, level_config)
    ui.render_narratives(report.narratives)
    ui.render_objectives(report.objectives)
    console.print()
    console.print("[dim]Edit the .sql files in dbt_project/models/ with your editor, then run [bold]stellar run[/bold][/dim]")


@app.command()
def run():
    """Run dbt and check objectives."""
    ui.render_header()
    report = GameEngine.run()
    ui.render_dbt_output(report.dbt_output, report.dbt_success)
    ui.render_newly_completed(report.newly_completed, report.objectives)

    if report.narratives:
        console.print()
        ui.render_narratives(report.narratives)

    if report.badge:
        ui.render_badge(report.badge, report.xp_earned)
    else:
        console.print()
        ui.render_objectives(report.objectives)


@app.command()
def test():
    """Run dbt test and check objectives."""
    ui.render_header()
    report = GameEngine.test()
    ui.render_dbt_output(report.dbt_output, report.dbt_success)
    ui.render_newly_completed(report.newly_completed, report.objectives)

    if report.narratives:
        console.print()
        ui.render_narratives(report.narratives)

    if report.badge:
        ui.render_badge(report.badge, report.xp_earned)
    else:
        console.print()
        ui.render_objectives(report.objectives)


@app.command()
def check():
    """Re-check file-based objectives without running dbt."""
    ui.render_header()
    report = GameEngine.check_objectives()
    ui.render_newly_completed(report.newly_completed, report.objectives)
    console.print()
    ui.render_objectives(report.objectives)


@app.command()
def status():
    """Show current game state, objectives, and progress."""
    ui.render_header()
    state, level, objectives = GameEngine.status()
    ui.render_status(state, level)
    ui.render_objectives(objectives)


@app.command()
def hint(objective: str = typer.Argument(None, help="Objective ID (omit to show all hints)")):
    """Show hint for an objective."""
    state = load_state()
    level = load_level(state.current_level)

    if objective:
        obj = next((o for o in level.objectives if o.id == objective), None)
        if obj:
            console.print(f"\n[bold]{obj.label}[/bold]")
            console.print(f"[yellow]  {obj.hint}[/yellow]\n")
        else:
            console.print(f"[red]Objective '{objective}' not found.[/red]")
            console.print(f"Available: {', '.join(o.id for o in level.objectives)}")
    else:
        for obj in level.objectives:
            console.print(f"\n[bold]{obj.id}:[/bold] {obj.label}")
            console.print(f"[yellow]  {obj.hint}[/yellow]")
        console.print()


@app.command()
def levels():
    """List all available levels."""
    state = load_state()
    for lvl in list_levels():
        done = "✅" if lvl["id"] in state.completed_levels else "⬜"
        current = " [cyan]← current[/cyan]" if lvl["id"] == state.current_level else ""
        console.print(f"  {done} Level {lvl['id']}: {lvl['title']}{current}")


@app.command()
def reset():
    """Restart the current level."""
    state = load_state()
    level_id = state.current_level
    # Clear level progress but keep XP/badges from other levels
    state.completed_objectives.pop(level_id, None)
    state.fired_triggers.pop(level_id, None)
    state.run_count = 0
    state.test_count = 0
    save_state(state)
    # Re-apply level files
    report = GameEngine.start_level(level_id)
    console.print(f"[yellow]Level {level_id} reset.[/yellow]")
    ui.render_narratives(report.narratives)
    ui.render_objectives(report.objectives)
