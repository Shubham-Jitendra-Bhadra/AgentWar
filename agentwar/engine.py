"""The turn engine: run agents in order each turn, then score.
mode='single' = one Red + one Blue (MVP). mode='squad' = the 8-agent pipelines."""
from __future__ import annotations
import re
from agentwar.referee import Referee
from agentwar.agent import Agent, Blackboard
from agentwar.prompts import RED_OPERATOR, BLUE_DEFENDER
from agentwar.squads import RED_SQUAD, BLUE_SQUAD
from agentwar.scoring import score
from agentwar.world import WorldState


class Game:
    def __init__(self, world: WorldState, max_turns: int = 5, model: str | None = None,
                 seed: int = 0, mode: str = "single", disabled: set | None = None):
        self.world = world
        self.ref = Referee(world, seed=seed)
        self.max_turns = max_turns
        self.mode = mode
        self.transcript: list[dict] = []
        disabled = disabled or set()

        if mode == "single":
            self.red_agents = [Agent("red-operator", "red", self.ref, RED_OPERATOR, model=model, max_steps=4)]
            self.blue_agents = [Agent("blue-defender", "blue", self.ref, BLUE_DEFENDER, model=model, max_steps=4)]
            self.red, self.blue = self.red_agents[0], self.blue_agents[0] 
        elif mode == "squad":
            red_bb, blue_bb = Blackboard(), Blackboard()
            self.red_agents = [
                Agent(r["name"], "red", self.ref, r["prompt"], tools=r["tools"],
                      blackboard=red_bb, model=model, max_steps=3)
                for r in RED_SQUAD if r["name"] not in disabled
            ]
            self.blue_agents = [
                Agent(b["name"], "blue", self.ref, b["prompt"], tools=b["tools"],
                      blackboard=blue_bb, model=model, max_steps=3)
                for b in BLUE_SQUAD if b["name"] not in disabled
            ]
        else:
            raise ValueError(f"unknown mode: {mode}")

    def run(self, verbose: bool = True) -> dict:
        for _ in range(self.max_turns):
            t = self.ref.advance_turn()
            for agent in self.red_agents + self.blue_agents:
                msgs = agent.take_turn(briefing=f"This is turn {t}.")
                self.transcript.append({"turn": t, "team": agent.team,
                                        "agent": agent.name, "messages": msgs})
                if verbose:
                    self._show(t, agent, msgs)
        return score(self.world)

    @staticmethod
    def _show(t, agent, msgs):
        for m in msgs:
            if m.get("role") == "assistant" and m.get("tool_calls"):
                for tc in m["tool_calls"]:
                    name = re.match(r"[a-zA-Z_]+", tc["function"]["name"]).group(0)
                    print(f"  [T{t}] {agent.name}: {name}({tc['function']['arguments']})")
            elif m.get("role") == "tool":
                print(f"        -> {m['content']}")
