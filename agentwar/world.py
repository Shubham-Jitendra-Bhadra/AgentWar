"""World state — the shared, simulated infra/org both teams fight over.

The Referee is the only component allowed to MUTATE this object. Agents read a
team-filtered *view* and request changes through tools, which the referee validates.
"""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field

Team = Literal["red", "blue"]


class Service(BaseModel):
    name: str
    exposed: bool = False        # reachable from outside
    patched: bool = True         # known vulns fixed
    compromised: bool = False    # red has control (hidden from blue)
    isolated: bool = False       # blue has quarantined it


class Credential(BaseModel):
    owner: str
    leaked: bool = False         # discoverable by red somewhere
    rotated: bool = True         # current (not stale/reused)
    stolen: bool = False         # red has obtained it (hidden from blue)


class Alert(BaseModel):
    turn: int
    source: str                  # which monitor/signal fired it
    message: str
    refers_to: str | None = None       # world fact it points at
    true_positive: bool | None = None  # filled in by the referee when scoring

class Signal(BaseModel):
    """Telemetry left behind by a red action. Blue's Monitor reads these."""
    turn: int
    kind: str                    # "port_scan", "exploit_attempt", "auth_anomaly", "data_egress"
    target: str | None = None
    strength: float = 0.5        # 0..1 — how loud / detectable
    is_attack: bool = True       # ground truth: real attack vs. benign noise


class Event(BaseModel):
    """One thing that happened — the post-game timeline is a list of these."""
    turn: int
    actor: str                   # agent name
    team: Team | Literal["referee"]
    action: str
    target: str | None = None
    success: bool = True
    detail: str = ""


class WorldState(BaseModel):
    services: list[Service] = Field(default_factory=list)
    credentials: list[Credential] = Field(default_factory=list)
    alerts_fired: list[Alert] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    turn: int = 0
    telemetry: list[Signal] = Field(default_factory=list)


    # ---- lookups ----
    def service(self, name: str) -> Service | None:
        return next((s for s in self.services if s.name == name), None)

    def credential(self, owner: str) -> Credential | None:
        return next((c for c in self.credentials if c.owner == owner), None)

    # ---- team-filtered views (the asymmetric-information core) ----
    def red_view(self) -> dict:
        """What red can see: only externally-visible facts. NOT patched/compromised."""
        visible = [s for s in self.services if s.exposed or s.compromised]
        return {
            "turn": self.turn,
            "services": [{"name": s.name, "exposed": s.exposed} for s in visible],
            "credentials": [
                {"owner": c.owner, "leaked": c.leaked}
                for c in self.credentials if c.leaked
            ],
        }

    def blue_view(self) -> dict:
        """What blue can see: posture, alerts, and telemetry — but NOT whether
        a signal is truly an attack (it has to judge that itself)."""
        return {
            "turn": self.turn,
            "services": [
                {"name": s.name, "exposed": s.exposed,
                 "patched": s.patched, "isolated": s.isolated}
                for s in self.services
            ],
            "credentials": [
                {"owner": c.owner, "rotated": c.rotated} for c in self.credentials
            ],
            "telemetry": [
                {"turn": s.turn, "kind": s.kind, "target": s.target, "strength": s.strength}
                for s in self.telemetry
            ],
            "alerts_fired": [a.model_dump() for a in self.alerts_fired],
        }
