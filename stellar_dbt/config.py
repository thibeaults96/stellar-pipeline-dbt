from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DBT_PROJECT_DIR = PROJECT_ROOT / "dbt_project"
GAME_STATE_PATH = PROJECT_ROOT / ".stellar_state.json"
DB_PATH = DBT_PROJECT_DIR / "stellar.duckdb"
LEVELS_DIR = Path(__file__).parent / "levels"
