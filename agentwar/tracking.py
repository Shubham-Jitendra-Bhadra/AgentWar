"""Log a finished game to Weights & Biases for the cross-run leaderboard."""
from __future__ import annotations
import os
import re
import wandb
from dotenv import load_dotenv

load_dotenv()


def _timeline_rows(transcript):
    """Flatten the transcript into (turn, team, action, args, result) rows."""
    rows = []
    for entry in transcript:
        turn, team = entry["turn"], entry["team"]
        pending = {}
        for m in entry["messages"]:
            if m.get("role") == "assistant" and m.get("tool_calls"):
                for tc in m["tool_calls"]:
                    name = re.match(r"[a-zA-Z_]+", tc["function"]["name"]).group(0)
                    pending[tc["id"]] = (name, tc["function"]["arguments"])
            elif m.get("role") == "tool":
                name, args = pending.get(m.get("tool_call_id"), ("?", "?"))
                rows.append([turn, team, name, args, m["content"]])
    return rows


def log_run(result: dict, config: dict, transcript=None) -> str:
    """Create a W&B run, log metrics + timeline, return the run URL."""
    run = wandb.init(
        entity=os.getenv("WANDB_ENTITY"),
        project=os.getenv("WANDB_PROJECT", "agentwar"),
        config=config,
        reinit=True,
    )

    # Scalar metrics -> these become the leaderboard columns.
    scalars = {k: v for k, v in result.items()
               if isinstance(v, (int, float)) and not isinstance(v, bool)}
    wandb.log(scalars)
    run.summary.update(scalars)
    run.summary["compromised_services"] = result["compromised_services"]
    run.summary["stolen_credentials"] = result["stolen_credentials"]

    if transcript is not None:
        table = wandb.Table(columns=["turn", "team", "action", "args", "result"])
        for row in _timeline_rows(transcript):
            table.add_data(*row)
        wandb.log({"timeline": table})

    url = run.url
    run.finish()
    return url
