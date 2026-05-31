"""OpenAI-style tool schemas for each team's actions.

Each tool name maps 1:1 to a Referee action handler. The Referee remains the
authority — these schemas just tell the model what moves it's allowed to request.
"""

def _fn(name, description, properties, required):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required},
        },
    }

_SERVICE = {"target": {"type": "string", "description": "name of the target service"}}
_OWNER = {"owner": {"type": "string", "description": "owner/name of the credential"}}
NOTE_TOOL = _fn(
    "note",
    "Record a brief finding, plan, or recommendation for your teammates to read.",
    {"text": {"type": "string", "description": "the note to share with your team"}},
    ["text"],
)




RED_TOOLS = [
    _fn("recon", "Probe an exposed service to learn whether it looks vulnerable.", _SERVICE, ["target"]),
    _fn("exploit", "Attempt to compromise a target service. Fails if it is patched or isolated.", _SERVICE, ["target"]),
    _fn("steal_cred", "Steal a leaked credential. Useless if it has been rotated.", _OWNER, ["owner"]),
    _fn("exfil", "Extract data from a service you have already compromised.", _SERVICE, ["target"]),
]

BLUE_TOOLS = [
    _fn("patch", "Patch a service so it can no longer be exploited.", _SERVICE, ["target"]),
    _fn("rotate_cred", "Rotate a credential so a stolen copy becomes useless.", _OWNER, ["owner"]),
    _fn("isolate", "Quarantine a service, blocking red from using or exfiltrating it.", _SERVICE, ["target"]),
    _fn("raise_alert",
        "Raise an alert about suspected malicious activity on a target.",
        {**_SERVICE, "message": {"type": "string", "description": "short description of what you suspect"}},
        ["target", "message"]),
]

ALL_TOOLS = RED_TOOLS + BLUE_TOOLS + [NOTE_TOOL]
TOOLS_BY_NAME = {t["function"]["name"]: t for t in ALL_TOOLS}
TOOLS_BY_TEAM = {"red": RED_TOOLS, "blue": BLUE_TOOLS}
