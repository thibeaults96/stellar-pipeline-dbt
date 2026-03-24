"""Rich-based terminal UI rendering for Stellar Pipeline."""
from __future__ import annotations

import re

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from stellar_dbt.models.game_types import (
    NarrativeEvent, ObjectiveDefinition, GameState, LevelConfig, EarnedBadge,
)
from stellar_dbt.ui.theme import CHARACTER_STYLES

console = Console()


def render_narrative(event: NarrativeEvent) -> None:
    style = CHARACTER_STYLES.get(event.character, "white")
    # Convert <highlight>text</highlight> to Rich markup
    message = re.sub(
        r"<highlight>(.*?)</highlight>",
        r"[bold cyan]\1[/bold cyan]",
        event.message,
    )
    panel = Panel(
        message,
        title=f"[{style}]{event.character}[/{style}]",
        border_style=style.replace("bold ", ""),
        box=box.ROUNDED,
        padding=(0, 1),
    )
    console.print(panel)


def render_narratives(events: list[NarrativeEvent]) -> None:
    for event in events:
        render_narrative(event)
        console.print()


def render_objectives(
    objectives: list[tuple[ObjectiveDefinition, bool, str | None]],
    completed_ids: set[str] | None = None,
) -> None:
    table = Table(
        title="MISSION OBJECTIVES",
        box=box.SIMPLE,
        show_header=False,
        padding=(0, 1),
        title_style="bold dim",
    )
    table.add_column("status", width=3)
    table.add_column("objective")

    for obj, passed, reason in objectives:
        if passed:
            status = Text("✅", style="green")
            label = Text(obj.label, style="dim strikethrough")
        else:
            status = Text("⬜", style="dim")
            label = Text(obj.label)
        table.add_row(status, label)
        if not passed and reason:
            table.add_row(Text(""), Text(f"  → {reason}", style="yellow"))

    console.print(table)


def render_newly_completed(
    newly: list[str],
    objectives: list[tuple[ObjectiveDefinition, bool, str | None]],
) -> None:
    if not newly:
        return
    for obj, _, _ in objectives:
        if obj.id in newly:
            console.print(f"  [bold green]✅ Objective complete:[/bold green] {obj.label}")


def render_badge(badge: EarnedBadge, xp: int) -> None:
    console.print()
    console.print(Panel(
        f"[bold]{badge.emoji}  {badge.name}[/bold]\n\n[bold cyan]+{xp} XP[/bold cyan]",
        title="[bold cyan]⚡ MISSION COMPLETE ⚡[/bold cyan]",
        border_style="cyan",
        box=box.DOUBLE,
        padding=(1, 2),
    ))


def render_status(state: GameState, level: LevelConfig) -> None:
    console.print(f"\n[bold cyan]STELLAR // PIPELINE[/bold cyan]  —  Level {level.id}: {level.title}")
    console.print(f"  XP: [bold cyan]{state.total_xp}[/bold cyan]  |  Badges: {' '.join(b.emoji for b in state.earned_badges) or 'none'}")
    console.print(f"  Runs: {state.run_count}  |  Tests: {state.test_count}")
    console.print()


def render_dbt_output(output: str, success: bool) -> None:
    if not output.strip():
        return
    style = "green" if success else "red"
    console.print(Panel(
        output.strip(),
        title=f"[{style}]dbt output[/{style}]",
        border_style="dim",
        box=box.SIMPLE,
        padding=(0, 1),
    ))


def render_header() -> None:
    console.print()
    console.print("[bold cyan]━━━ STELLAR // PIPELINE ━━━[/bold cyan]")
    console.print()
