"""Referee — owns the world state and is the ONLY writer.

Every action goes through apply(): it validates legality against the hidden
truth, mutates the world, logs an Event, emits telemetry for red actions, and
returns an observation describing what the acting agent learns.
"""
from __future__ import annotations
import random

from matplotlib.pylab import seed
from agentwar.world import WorldState, Alert, Event, Signal


class Referee:
    def __init__(self, world: WorldState, seed: int = 0):
        self.world = world
        self.rng = random.Random(seed)

    # ---- public API ----
    def apply(self, *, actor: str, team: str, action: str, **params) -> dict:
        handler = self._handlers().get((team, action))
        if handler is None:
            return self._fail(actor, team, action, params.get("target"),
                              f"unknown action '{action}' for team '{team}'")
        return handler(actor, params)

    def advance_turn(self) -> int:
        self.world.turn += 1
        self._inject_noise()                
        return self.world.turn

    def _inject_noise(self):
        """Emit 0-2 benign signals that look superficially like attacks.
        These are is_attack=False, so alerting on them = a false positive."""
        kinds = ["port_scan", "auth_anomaly", "data_egress"]
        names = [s.name for s in self.world.services] + [c.owner for c in self.world.credentials]
        if not names:
            return
        for _ in range(self.rng.randint(0, 2)):
            self._signal(
                kind=self.rng.choice(kinds),
                target=self.rng.choice(names),
                strength=round(self.rng.uniform(0.1, 0.5), 1),  # noise stays weak-ish
                is_attack=False,
            )
    # ---- internal helpers ----
    def _log(self, actor, team, action, target, success, detail):
        self.world.events.append(Event(turn=self.world.turn, actor=actor, team=team,
                                        action=action, target=target,
                                        success=success, detail=detail))

    def _fail(self, actor, team, action, target, reason):
        self._log(actor, team, action, target, False, reason)
        return {"ok": False, "error": reason}

    def _signal(self, kind, target, strength, is_attack=True):
        self.world.telemetry.append(Signal(turn=self.world.turn, kind=kind,
                                            target=target, strength=strength,
                                            is_attack=is_attack))

    def _handlers(self):
        return {
            ("red", "recon"): self._red_recon,
            ("red", "exploit"): self._red_exploit,
            ("red", "steal_cred"): self._red_steal_cred,
            ("red", "exfil"): self._red_exfil,
            ("blue", "patch"): self._blue_patch,
            ("blue", "rotate_cred"): self._blue_rotate_cred,
            ("blue", "isolate"): self._blue_isolate,
            ("blue", "raise_alert"): self._blue_raise_alert,
        }

    # ---- RED actions ----
    def _red_recon(self, actor, p):
        target = p.get("target"); svc = self.world.service(target)
        if svc is None or not (svc.exposed or svc.compromised):
            return self._fail(actor, "red", "recon", target, "target not visible to red")
        self._signal("port_scan", target, 0.3)
        self._log(actor, "red", "recon", target, True, "probed service")
        return {"ok": True, "target": target, "exposed": svc.exposed,
                "looks_vulnerable": not svc.patched}

    def _red_exploit(self, actor, p):
        target = p.get("target"); svc = self.world.service(target)
        if svc is None or not (svc.exposed or svc.compromised):
            return self._fail(actor, "red", "exploit", target, "target not reachable")
        if svc.isolated:
            self._signal("exploit_attempt", target, 0.9)
            return self._fail(actor, "red", "exploit", target, "target isolated")
        if svc.patched:
            self._signal("exploit_attempt", target, 0.8)   # failed = loud
            return self._fail(actor, "red", "exploit", target, "exploit failed (patched)")
        svc.compromised = True
        self._signal("exploit_attempt", target, 0.7)
        self._log(actor, "red", "exploit", target, True, "service compromised")
        return {"ok": True, "target": target, "compromised": True}

    def _red_steal_cred(self, actor, p):
        owner = p.get("owner"); cred = self.world.credential(owner)
        if cred is None or not cred.leaked:
            return self._fail(actor, "red", "steal_cred", owner, "credential not discoverable")
        if cred.rotated:
            self._signal("auth_anomaly", owner, 0.4)
            return self._fail(actor, "red", "steal_cred", owner, "credential rotated, useless")
        cred.stolen = True
        self._signal("auth_anomaly", owner, 0.2)            # quiet
        self._log(actor, "red", "steal_cred", owner, True, "credential stolen")
        return {"ok": True, "owner": owner, "stolen": True}

    def _red_exfil(self, actor, p):
        target = p.get("target"); svc = self.world.service(target)
        if svc is None or not svc.compromised:
            return self._fail(actor, "red", "exfil", target, "target not compromised")
        if svc.isolated:
            return self._fail(actor, "red", "exfil", target, "target isolated, egress blocked")
        self._signal("data_egress", target, 0.6)
        self._log(actor, "red", "exfil", target, True, "data exfiltrated")
        return {"ok": True, "target": target, "exfiltrated": True}

    # ---- BLUE actions ----
    def _blue_patch(self, actor, p):
        target = p.get("target"); svc = self.world.service(target)
        if svc is None:
            return self._fail(actor, "blue", "patch", target, "no such service")
        svc.patched = True
        self._log(actor, "blue", "patch", target, True, "service patched")
        return {"ok": True, "target": target, "patched": True}

    def _blue_rotate_cred(self, actor, p):
        owner = p.get("owner"); cred = self.world.credential(owner)
        if cred is None:
            return self._fail(actor, "blue", "rotate_cred", owner, "no such credential")
        cred.rotated = True
        self._log(actor, "blue", "rotate_cred", owner, True, "credential rotated")
        return {"ok": True, "owner": owner, "rotated": True}

    def _blue_isolate(self, actor, p):
        target = p.get("target"); svc = self.world.service(target)
        if svc is None:
            return self._fail(actor, "blue", "isolate", target, "no such service")
        svc.isolated = True
        self._log(actor, "blue", "isolate", target, True, "service isolated")
        return {"ok": True, "target": target, "isolated": True}

    def _blue_raise_alert(self, actor, p):
        refers_to = p.get("refers_to"); message = p.get("message", "")
        real = any(s.is_attack and s.target == refers_to for s in self.world.telemetry)
        self.world.alerts_fired.append(
            Alert(turn=self.world.turn, source=actor, message=message,
                  refers_to=refers_to, true_positive=real))
        self._log(actor, "blue", "raise_alert", refers_to, True,
                  f"{'TP' if real else 'FP'}: {message}")
        return {"ok": True, "refers_to": refers_to, "true_positive": real}
