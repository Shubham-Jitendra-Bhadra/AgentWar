from agentwar.llm import chat

tools = [{
    "type": "function",
    "function": {
        "name": "exploit",
        "description": "Attempt to compromise a target service.",
        "parameters": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "name of the service to attack"}
            },
            "required": ["target"],
        },
    },
}]

msg = chat(
    messages=[
        {"role": "system", "content": "You are a red-team exploit agent. Act using the provided tools."},
        {"role": "user", "content": "Recon found 's3-data-bucket' is exposed and unpatched. Attack it."},
    ],
    tools=tools,
    max_tokens=300,
)

print("CONTENT:   ", msg.content)
print("TOOL CALLS:", msg.tool_calls)
