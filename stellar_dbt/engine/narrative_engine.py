"""Narrative engine — triggers character dialogue based on game events."""
from __future__ import annotations

from stellar_dbt.models.game_types import NarrativeTrigger, NarrativeEvent


def process(
    events: list[str],
    triggers: list[NarrativeTrigger],
    script: dict[str, NarrativeEvent],
    fired_triggers: set[str],
) -> tuple[list[NarrativeEvent], set[str]]:
    """Given game events, return narrative messages to display and updated fired set."""
    new_queue: list[NarrativeEvent] = []
    new_fired = set(fired_triggers)

    for event in events:
        for trigger in triggers:
            if trigger.event != event:
                continue
            if trigger.once and trigger.id in new_fired:
                continue
            narrative = script.get(trigger.narrative_key)
            if not narrative:
                continue
            new_queue.append(narrative)
            new_fired.add(trigger.id)

    priority_order = {"high": 0, "normal": 1, "low": 2}
    new_queue.sort(key=lambda e: priority_order.get(e.priority, 1))

    return new_queue, new_fired
