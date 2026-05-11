"""Narrative engine — triggers character dialogue based on game events."""
from __future__ import annotations

from stellar_dbt.models.game_types import NarrativeTrigger, NarrativeEvent


def process(
    events: list[str],
    triggers: list[NarrativeTrigger],
    script: dict[str, NarrativeEvent],
    fired_triggers: set[str],
    completed_objectives: set[str] | None = None,
) -> tuple[list[NarrativeEvent], set[str]]:
    """Given game events, return narrative messages to display and updated fired set."""
    new_queue: list[NarrativeEvent] = []
    new_fired = set(fired_triggers)
    completed = completed_objectives or set()
    queued_keys: set[str] = set()

    for event in events:
        for trigger in triggers:
            trigger_events = (
                trigger.event if isinstance(trigger.event, list) else [trigger.event]
            )
            if event not in trigger_events:
                continue
            if trigger.once and trigger.id in new_fired:
                continue
            if trigger.requires and not all(r in completed for r in trigger.requires):
                continue
            if trigger.narrative_key in queued_keys:
                # Same narrative would be queued twice in one batch (e.g. two
                # events satisfy the same trigger). Mark this trigger fired so
                # `once` semantics still hold, but don't duplicate the message.
                new_fired.add(trigger.id)
                continue
            narrative = script.get(trigger.narrative_key)
            if not narrative:
                continue
            new_queue.append(narrative)
            queued_keys.add(trigger.narrative_key)
            new_fired.add(trigger.id)

    priority_order = {"high": 0, "normal": 1, "low": 2}
    new_queue.sort(key=lambda e: priority_order.get(e.priority, 1))

    return new_queue, new_fired
