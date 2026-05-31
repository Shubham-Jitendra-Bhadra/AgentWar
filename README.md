# AgentWar

Two AI agent teams fight over a shared, simulated world. **Red** attacks, **Blue** defends, and a neutral **Referee** owns the ground truth and keeps score. Every move is made by a agent with tool use, and you watch their reasoning play out turn by turn on a live leaderboard.

## Core Concept

Red team finds weaknesses and executes attacks. Blue team detects, responds, and hardens. The referee validates every action against the real world state and scores the run on **dwell time**, **blast radius**, and **detection latency**.

What makes it interesting:

- **Agents can be wrong.** Recon can hallucinate a vuln; Monitor can miss an obvious signal. That's realistic — and fun to watch.
- **Asymmetric information.** Red can't see Blue's internal state and vice versa. This forces real strategy, not just tool spam.
- **Ablations.** Drop the Forensics agent and watch dwell time explode. Each agent earns its place.
- **Quantitative output.** The referee's scores feed a leaderboard you can compare across runs and scenarios.

## Agents

### 🔴 Red Team
| Agent | Role |
|-------|------|
| **Recon** | Enumerates attack surface — open ports, exposed APIs, org chart, public info |
| **Planner** | Prioritizes targets, sequences attack steps |
| **Exploit** | Executes specific attack actions against world state |
| **Exfil** | Extracts value — data, credentials, persistence |

### 🔵 Blue Team
| Agent | Role |
|-------|------|
| **Monitor** | Watches world state for anomalies, generates alerts |
| **Triage** | Classifies alerts — real vs. noise |
| **Responder** | Patches, blocks, isolates based on triage |
| **Forensics** | Post-incident, reconstructs what happened and hardens defenses |

### ⚪ Neutral
| Agent | Role |
|-------|------|
| **Referee** | Owns world state, validates action legality, scores outcomes. The only agent with write access to ground truth. |

## World State

A simple JSON object both teams read/write through tools (Referee validates every write):

```json
{
  "services": [{ "name": "...", "exposed": false, "patched": true, "compromised": false }],
  "credentials": [{ "owner": "...", "leaked": false, "rotated": true }],
  "alerts_fired": [],
  "turn": 0
}
```

## Demo Flow

1. **Load a scenario** — e.g. "startup with 3 microservices, one misconfigured S3 bucket, weak credential rotation."
2. **Watch turns in real time** — agent reasoning streams alongside world state changes, side by side.
3. **End state** — a timeline of the attack, what Blue caught vs. missed, and the final score.

## Scoring

| Metric | Meaning |
|--------|---------|
| **Dwell time** | How long Red operated undetected |
| **Blast radius** | How many services/credentials were compromised |
| **Detection latency** | Turns between an attack and the alert that caught it |

## Tech Stack

- **Claude API** with tool use — powers every agent
- **Weights & Biases** — inference (W&B Inference) + experiment tracking across runs
- **Shared world state** — in-memory or Postgres
- **React frontend** — streams agent thoughts for the live visualization
- **Referee** — the single source of write-access to ground truth

## Status

🚧 Early development — hackathon project.
