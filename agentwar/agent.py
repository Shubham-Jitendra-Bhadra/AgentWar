"""Generic agent: see your view, think, call Referee tools, repeat."""
from __future__ import annotations
import re
import json
from agentwar import tools
from agentwar.llm import chat
from agentwar.tools import TOOLS_BY_TEAM, TOOLS_BY_NAME
import weave

from agentwar.tools import TOOLS_BY_TEAM, TOOLS_BY_NAME

_ARG_ALIASES = {"raise_alert": {"target": "refers_to"}}

class Blackboard:
    """Per-team shared memory. Agents write findings/plans; teammates read them."""
    def __init__(self):
        self.notes: list[dict] = []

    def add(self, turn: int, author: str, text: str):
        self.notes.append({"turn": turn, "author": author, "text": text})

    def recent(self, n: int = 12) -> list[dict]:
        return self.notes[-n:]
class Agent:
    def __init__(self, name, team, referee, system_prompt, tools=None,
                 blackboard=None, model=None, max_steps=4):
        self.name = name
        self.team = team
        self.referee = referee
        self.system_prompt = system_prompt
        self.model = model
        self.max_steps = max_steps
        self.blackboard = blackboard
        self.tools = TOOLS_BY_TEAM[team] if tools is None else [TOOLS_BY_NAME[t] for t in tools]

    def _view(self) -> dict:
        w = self.referee.world
        view = w.red_view() if self.team == "red" else w.blue_view()
        if self.blackboard is not None:
            view = {**view, "team_intel": self.blackboard.recent()}
        return view


    def _run_tool(self, tool_call) -> dict:
        raw = tool_call.function.name or ""
        m = re.match(r"[a-zA-Z_]+", raw)
        name = m.group(0) if m else raw
        args = json.loads(tool_call.function.arguments or "{}")
        if name == "note":
            text = args.get("text", "")
            if self.blackboard is not None:
                self.blackboard.add(self.referee.world.turn, self.name, text)
            return {"ok": True, "noted": text}
        for src, dst in _ARG_ALIASES.get(name, {}).items():
            if src in args:
                args[dst] = args.pop(src)
        return self.referee.apply(actor=self.name, team=self.team, action=name, **args)

    @weave.op
    def take_turn(self, briefing: str = "") -> list[dict]:
        """Run one turn. Returns the message transcript for logging/visualization."""
        view = json.dumps(self._view(), indent=2)
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content":
                f"Current observation:\n{view}\n\n{briefing}\n"
                "Decide your move(s) for this turn using the tools. "
                "Stop when you've done what makes sense this turn."},
        ]

        for _ in range(self.max_steps):
            msg = chat(messages, tools=self.tools, model=self.model)
            messages.append(msg.model_dump(exclude_none=True))
            if not msg.tool_calls:
                break                                  # agent chose to stop
            for tc in msg.tool_calls:
                result = self._run_tool(tc)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result),
                })
        return messages
