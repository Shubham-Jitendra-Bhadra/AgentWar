# AgentWar — Agents

AgentWar pits two AI agent teams against each other over a shared, simulated
world. **Red** attacks, **Blue** defends, and a neutral **Referee** owns the
ground truth and keeps score. Every agent is an LLM with a focused role and a
restricted set of tools; the Referee is plain code and the only writer of truth.

---

## 🔴 Red Squad — pipeline: recon → planner → exploit → exfil

| Agent | Tools | Role |
|-------|-------|------|
| **Recon** | `recon`, `note` | Probes the externally-visible surface; reports which services are exposed/vulnerable and which credentials are leaked. Cannot exploit — intel only. |
| **Planner** | `note` | Touches nothing in the world. Reads Recon's findings and writes a prioritized, sequenced attack plan for the team. |
| **Exploit** | `exploit`, `note` | Executes the plan, compromising prioritized targets (only unpatched, reachable services succeed). |
| **Exfil** | `steal_cred`, `exfil`, `note` | Extracts value: steals leaked, un-rotated credentials and exfiltrates data from compromised services. |

## 🔵 Blue Squad — pipeline: monitor → triage → responder → forensics

| Agent | Tools | Role |
|-------|-------|------|
| **Monitor** | `note` | Watches telemetry; separates likely-real signals from benign noise and flags candidate incidents. Cannot raise alerts — only nominates. |
| **Triage** | `raise_alert`, `note` | Decides which candidates are real enough to alert on, balancing false positives (costly) against misses (costlier). |
| **Responder** | `patch`, `rotate_cred`, `isolate`, `note` | Acts on confirmed alerts: isolates services under attack, patches exposed ones, rotates leaked credentials. |
| **Forensics** | `isolate`, `patch`, `note` | Post-incident sweep. Reconstructs intrusions the team MISSED (e.g. data egress nobody alerted on ⇒ likely compromise) and contains them. This is the agent the ablation removes. |

## ⚪ Neutral

| Agent | Role |
|-------|------|
| **Referee** | Not an LLM — pure code. Owns the world state, validates every action against the hidden truth, flips the real flags, emits telemetry, injects benign noise, and scores the run. The only component with write access. |

---

## Coordination

Each team shares a **blackboard** (`team_intel`) — a running list of `note`s
injected into every teammate's view. This is how the pipeline passes
information: Recon's findings reach Planner, the plan reaches Exploit, Monitor's
candidates reach Triage, and so on. The two teams' blackboards are **separate** —
neither side ever sees the other's.

## Tools (all validated by the Referee)

| Team | Tool | Effect |
|------|------|--------|
| Red | `recon(target)` | Probe an exposed service; reveals whether it looks vulnerable. |
| Red | `exploit(target)` | Compromise a service. Fails if it is patched or isolated. |
| Red | `steal_cred(owner)` | Steal a leaked credential. Useless if it has been rotated. |
| Red | `exfil(target)` | Extract data from an already-compromised service. |
| Blue | `patch(target)` | Patch a service so it can no longer be exploited. |
| Blue | `rotate_cred(owner)` | Rotate a credential so a stolen copy becomes useless. |
| Blue | `isolate(target)` | Quarantine a service, blocking exploit/exfil. |
| Blue | `raise_alert(target, message)` | Flag suspected malicious activity (scored TP/FP). |
| Both | `note(text)` | Share a finding/plan with teammates via the blackboard. |

---

## Turn Flow

    For each turn (1…N):

      Referee.advance_turn()
        → turn++, inject benign noise signals

      RED acts in pipeline order:
        recon ─► planner ─► exploit ─► exfil
        (each reads team_intel + its filtered red_view, calls tools,
         writes notes; Referee validates and emits attack telemetry)

      BLUE acts in pipeline order:
        monitor ─► triage ─► responder ─► forensics
        (each reads team_intel + its blue_view incl. telemetry,
         calls tools; Referee validates and scores alerts as TP/FP)

    After N turns → Referee scores the run:
      blast radius · dwell time · detection latency · TP/FP alerts

Each agent runs a small **see → think → act** loop on its move (up to
`max_steps` tool calls), reacting to each tool result before deciding its next
action. That feedback loop is why Exploit can recover after a rejected action
and Triage can decide *not* to alert.

---

## Design Properties

- **Agents can be wrong.** Recon can misjudge a target, Monitor can dismiss a
  real signal, Triage can fire a false positive. Mistakes come from the LLM's
  judgment, not random dice — so runs stay reproducible.
- **Asymmetric information.** Red sees only the exposed surface; Blue sees
  posture + telemetry but never the hidden `compromised`/`stolen` flags. Each
  team's blackboard is private.
- **Ablatable.** Disable any agent (`disabled={"forensics"}`) and measure the
  score change. Removing Forensics is expected to raise dwell time, since nobody
  catches the breaches that detection missed.

## Scoring

| Metric | Meaning |
|--------|---------|
| **Blast radius** | Services compromised + credentials stolen. |
| **Dwell time** | Turns a breach stayed live before detection/containment. |
| **Detection latency** | Turns between the first attack signal and the first true-positive alert. |
| **TP / FP alerts** | True vs. false positive alerts raised by Blue. |

---

## Example Dry Run

**Scenario:** `startup` — `api-gateway` (exposed, patched), `auth-service`
(hidden, patched), `billing-service` (hidden, unpatched), `s3-data-bucket`
(exposed, **unpatched**); leaked & un-rotated creds `ci-deploy-key`,
`s3-access-key`; clean `admin`. **Mode:** squad, 2 turns shown.

### Turn 1

**🔴 Red**

    recon    recon(api-gateway)    → {exposed:true, looks_vulnerable:false}
             recon(s3-data-bucket) → {exposed:true, looks_vulnerable:true}
             note → "api-gateway hardened; s3-data-bucket exposed+vulnerable;
                     leaked creds: ci-deploy-key, s3-access-key"
    planner  note → "Plan: (1) exploit s3-data-bucket  (2) steal s3-access-key
                     (3) exfil s3-data-bucket.  Skip api-gateway — patched."
    exploit  exploit(s3-data-bucket) → {compromised:true}
             note → "s3-data-bucket is OURS"
    exfil    steal_cred(s3-access-key) → {stolen:true}
             exfil(s3-data-bucket)     → {exfiltrated:true}
             note → "stole s3-access-key, exfiltrated bucket data"

    Telemetry now: port_scan×2 (0.3), exploit_attempt s3 (0.7),
                   auth_anomaly s3-access-key (0.2), data_egress s3 (0.6),
                   + 1 benign noise signal on auth-service (0.2)

**🔵 Blue**

    monitor    note → "Strong: exploit_attempt(0.7) + data_egress(0.6) on
                       s3-data-bucket ⇒ likely intrusion. Weak auth_anomaly on
                       s3-access-key (0.2). auth-service blip looks like noise."
    triage     raise_alert(s3-data-bucket, "exploit + egress") → {true_positive:true}
               note → "Confirmed s3-data-bucket. Dismissed weak/noise signals."
    responder  isolate(s3-data-bucket)      → {isolated:true}
               rotate_cred(s3-access-key)   → {rotated:true}
               patch(billing-service)       → {patched:true}   (proactive)
               note → "Contained s3-data-bucket; rotated key; hardened billing."
    forensics  note → "s3 egress already contained; no other missed compromise."

### Turn 2

**🔴 Red** (locked out)

    exploit    exploit(s3-data-bucket)   → {ok:false, "target isolated"}
    exfil      steal_cred(s3-access-key) → {ok:false, "credential rotated, useless"}
               recon(api-gateway)        → {looks_vulnerable:false}   (still hardened)

**🔵 Blue**

    monitor    note → "New loud exploit_attempt(0.9) on isolated s3 — contained."
    triage     raise_alert(s3-data-bucket, "repeat exploit attempt") → {true_positive:true}
    responder  (nothing new to contain)
    forensics  note → "No missed activity. Posture holding."

### Final Score (illustrative)

    blast_radius          2     (s3-data-bucket compromised + s3-access-key stolen)
    exfiltrations         1     (Red got ONE batch out before containment)
    total_dwell_time      0     (Blue isolated the breach the same turn)
    avg_detection_latency 1.0
    true_positive_alerts  2
    false_positive_alerts 0     (Triage correctly dismissed the noise)
    attacks_missed        1     (the s3-access-key auth_anomaly was never alerted)

**Read:** Blue wins on containment (dwell 0, no false alarms), but Red still
scores one exfiltration in the opening turn — the cost of detection latency.
Note `attacks_missed: 1`: nobody alerted on the quiet credential-theft signal,
which is exactly the kind of gap the **Forensics** ablation makes worse.

---

## Reading the Example

A plain-English walkthrough of the dry run above.

### Setup
Four assets. Two are internet-reachable — `api-gateway` (patched, hard) and
`s3-data-bucket` (unpatched, soft). Two are internal/hidden — `auth-service`
and `billing-service`. Two leaked, un-rotated keys lie around; `admin` is clean.
**Red cannot see all this** — only the two exposed services and the two leaked
keys. Everything else must be discovered.

### Turn 1 — Red breaks in
- **Recon** only looks. It probes both exposed services, learns the bucket
  "looks vulnerable" and the gateway doesn't, and writes that to the blackboard.
  It has no `exploit` tool — intel is its entire job.
- **Planner** has *no world tools at all* — it just thinks. Reading Recon's
  note, it produces a plan (hit the bucket, steal the matching key, exfiltrate)
  and explicitly skips the hardened gateway. The "don't attack a locked door"
  intelligence lives in a dedicated brain.
- **Exploit** runs the plan: `exploit(s3-data-bucket)` → the Referee flips the
  hidden `compromised` flag.
- **Exfil** cashes in: steals `s3-access-key` (works — never rotated) and
  exfiltrates the data. **This is Red's payoff: one batch is out.**

Every Red action left telemetry — a loud `exploit_attempt` (0.7), a
`data_egress` (0.6), a quiet `auth_anomaly` (0.2) — plus one *benign* noise
signal the Referee injected. Blue must now sort real from fake.

### Turn 1 — Blue responds
- **Monitor** can't act (no alert tool); it judges. It calls the strong,
  correlated bucket signals "likely intrusion," dismisses the weak noise, and
  writes candidates.
- **Triage** raises exactly **one** alert — on the bucket — scored a true
  positive. It ignores the noise, which is why FP stays 0.
- **Responder** contains: `isolate`s the bucket, `rotate`s the stolen key, and
  proactively patches `billing-service` — which it can see is unpatched because
  **Blue sees internal posture Red can't.** Asymmetry running the other way.
- **Forensics** sweeps, finds the breach already contained, holds posture.

### Turn 2 — Red is stuck
`exploit` → "target isolated." `steal_cred` → "credential rotated, useless."
Red's wins are neutralized; Blue just confirms the harmless repeat attempt.

### What the score says
| Metric | Value | Meaning |
|--------|-------|---------|
| `blast_radius: 2` | bucket + key | Red did real damage |
| `exfiltrations: 1` | one batch escaped | Red scored before Blue reacted |
| `total_dwell_time: 0` | contained same turn | fast response |
| `false_positive_alerts: 0` | noise dismissed | good Triage judgment |
| `attacks_missed: 1` | quiet key-theft signal | never alerted on |

**Headline:** Blue wins on containment, but not cleanly. Red still lands one
exfiltration in the opening window — that's what detection latency *costs* — and
the quiet credential-theft signal slips through unnoticed.

### Why this is the whole pitch in miniature
- **The pipeline works:** trace Planner's note → Exploit's action, and Monitor's
  note → Triage's alert. The blackboard is doing its job.
- **Asymmetry both ways:** Red is blind to internal services; Blue is blind to
  what's actually compromised and must infer from telemetry.
- **Agents right *and* wrong in one game:** Triage correctly ignores noise, yet
  the team collectively misses the credential-theft signal.
- **It sets up the ablation:** that `attacks_missed: 1` is exactly the gap
  **Forensics** is meant to close on later turns. Remove Forensics and gaps like
  it stay open longer — dwell time climbs.
