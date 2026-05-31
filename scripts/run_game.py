import json
from agentwar.scenarios import load_scenario
from agentwar.engine import Game
from agentwar.tracking import log_run
import weave
from dotenv import load_dotenv
import os

load_dotenv()
weave.init(f"{os.getenv('WANDB_ENTITY')}/{os.getenv('WANDB_PROJECT', 'agentwar')}")

SCENARIO, MAX_TURNS, SEED = "startup", 5, 0
    
world = load_scenario(SCENARIO)
game = Game(world, max_turns=MAX_TURNS, seed=SEED)

print("================ GAME START ================")
result = game.run(verbose=True)

print("\n================ FINAL SCORE ================")
print(json.dumps(result, indent=2))

url = log_run(
    result=result,
    config={"scenario": SCENARIO, "max_turns": MAX_TURNS, "seed": SEED,
            "model": game.red.model or "default"},
    transcript=game.transcript,
)
print("\nLogged to W&B:", url)
