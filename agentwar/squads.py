"""Squad definitions: which role gets which tools and prompt."""
from agentwar.prompts import (
    RECON, PLANNER, EXPLOIT_RED, EXFIL,
    MONITOR, TRIAGE, RESPONDER, FORENSICS,
)

RED_SQUAD = [
    {"name": "recon",    "tools": ["recon", "note"],                      "prompt": RECON},
    {"name": "planner",  "tools": ["note"],                              "prompt": PLANNER},
    {"name": "exploit",  "tools": ["exploit", "note"],                   "prompt": EXPLOIT_RED},
    {"name": "exfil",    "tools": ["steal_cred", "exfil", "note"],       "prompt": EXFIL},
]

BLUE_SQUAD = [
    {"name": "monitor",   "tools": ["note"],                                  "prompt": MONITOR},
    {"name": "triage",    "tools": ["raise_alert", "note"],                   "prompt": TRIAGE},
    {"name": "responder", "tools": ["patch", "rotate_cred", "isolate", "note"], "prompt": RESPONDER},
    {"name": "forensics", "tools": ["isolate", "patch", "note"],              "prompt": FORENSICS},
]
