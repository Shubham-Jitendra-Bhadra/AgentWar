"""Load starting scenarios into a WorldState."""
from __future__ import annotations
from pathlib import Path
from agentwar.world import WorldState

SCENARIO_DIR = Path(__file__).resolve().parent.parent / "scenarios"


def load_scenario(name: str = "startup") -> WorldState:
    """Read scenarios/<name>.json and build a validated WorldState."""
    path = SCENARIO_DIR / f"{name}.json"
    if not path.exists():
        available = [p.stem for p in SCENARIO_DIR.glob("*.json")]
        raise FileNotFoundError(f"No scenario '{name}'. Available: {available}")
    return WorldState.model_validate_json(path.read_text(encoding="utf-8"))
