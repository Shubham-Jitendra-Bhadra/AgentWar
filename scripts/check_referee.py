from agentwar.scenarios import load_scenario
from agentwar.referee import Referee

w = load_scenario()
ref = Referee(w)

print("recon  :", ref.apply(actor="recon", team="red", action="recon", target="s3-data-bucket"))
print("exploit:", ref.apply(actor="exploit", team="red", action="exploit", target="s3-data-bucket"))
print("exp-fail:", ref.apply(actor="exploit", team="red", action="exploit", target="api-gateway"))
print("steal  :", ref.apply(actor="exfil", team="red", action="steal_cred", owner="s3-access-key"))
print("exfil  :", ref.apply(actor="exfil", team="red", action="exfil", target="s3-data-bucket"))
ref.advance_turn()
print("alert  :", ref.apply(actor="monitor", team="blue", action="raise_alert",
                            refers_to="s3-data-bucket", message="egress spike"))
print("isolate:", ref.apply(actor="responder", team="blue", action="isolate", target="s3-data-bucket"))
print("\nTELEMETRY:")
for s in w.telemetry: print("  ", s.model_dump())
print("ALERTS:")
for a in w.alerts_fired: print("  ", a.model_dump())
