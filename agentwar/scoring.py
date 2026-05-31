"""Score a finished game on the metrics from the spec."""
from __future__ import annotations
from agentwar.world import WorldState


def score(world: WorldState) -> dict:
    final_turn = world.turn
    compromised = [s for s in world.services if s.compromised]
    stolen = [c for c in world.credentials if c.stolen]
    exfils = [e for e in world.events if e.action == "exfil" and e.success]

    def first_turn(pred):
        ts = [e.turn for e in world.events if pred(e)]
        return min(ts) if ts else None


    dwell = {}
    for s in compromised:
        c_turn = first_turn(lambda e: e.action == "exploit" and e.success and e.target == s.name)
        tp = [a.turn for a in world.alerts_fired if a.refers_to == s.name and a.true_positive]
        iso = first_turn(lambda e: e.action == "isolate" and e.success and e.target == s.name)
        caught = [t for t in (tp + [iso]) if t is not None]
        end = min(caught) if caught else final_turn
        if c_turn is not None:
            dwell[s.name] = max(0, end - c_turn)

    # Detection latency: first attack signal on a target -> first true-positive alert.
    attacked = {sig.target for sig in world.telemetry if sig.is_attack}
    latencies, detected = [], 0
    for tgt in attacked:
        first_sig = min(sig.turn for sig in world.telemetry if sig.is_attack and sig.target == tgt)
        tp = [a.turn for a in world.alerts_fired if a.refers_to == tgt and a.true_positive]
        if tp:
            latencies.append(min(tp) - first_sig)
            detected += 1

    tp_alerts = sum(1 for a in world.alerts_fired if a.true_positive)
    fp_alerts = sum(1 for a in world.alerts_fired if a.true_positive is False)

    return {
        "turns_played": final_turn,
        "blast_radius": len(compromised) + len(stolen),
        "compromised_services": [s.name for s in compromised],
        "stolen_credentials": [c.owner for c in stolen],
        "exfiltrations": len(exfils),
        "total_dwell_time": sum(dwell.values()),
        "dwell_by_service": dwell,
        "avg_detection_latency": (sum(latencies) / len(latencies)) if latencies else None,
        "attacks_detected": detected,
        "attacks_missed": len(attacked) - detected,
        "true_positive_alerts": tp_alerts,
        "false_positive_alerts": fp_alerts,
    }
