"""Load/save game state to a JSON file."""
from __future__ import annotations

import json
from stellar_dbt.config import GAME_STATE_PATH
from stellar_dbt.models.game_types import GameState


def load_state() -> GameState:
    if GAME_STATE_PATH.exists():
        data = json.loads(GAME_STATE_PATH.read_text())
        return GameState(**data)
    return GameState()


def save_state(state: GameState) -> None:
    GAME_STATE_PATH.write_text(state.model_dump_json(indent=2))
