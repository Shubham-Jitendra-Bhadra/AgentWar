"""Smoke-test the W&B Inference endpoint before building anything on it."""
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url=os.environ["WANDB_BASE_URL"],
    api_key=os.environ["WANDB_API_KEY"],
    project=f"{os.environ['WANDB_ENTITY']}/{os.environ['WANDB_PROJECT']}",
)

resp = client.chat.completions.create(
    model=os.environ["WANDB_MODEL"],
    messages=[
        {"role": "system", "content": "You are a terse assistant."},
        {"role": "user", "content": "Reply with exactly: AgentWar inference OK"},
    ],
    max_tokens=300,          # room for reasoning + the actual answer
)

msg = resp.choices[0].message
print("MODEL:        ", os.environ["WANDB_MODEL"])
print("FINISH REASON:", resp.choices[0].finish_reason)
print("CONTENT:      ", msg.content)
print("REASONING:    ", getattr(msg, "reasoning", None))
print("USAGE:        ", resp.usage)
