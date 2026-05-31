"""Thin LLM client over the W&B Inference (OpenAI-compatible) endpoint."""
from __future__ import annotations
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_client: OpenAI | None = None
DEFAULT_MODEL = os.getenv("WANDB_MODEL", "openai/gpt-oss-20b")


def get_client() -> OpenAI:
    """Lazily build a single shared client (reuses the connection pool)."""
    global _client
    if _client is None:
        _client = OpenAI(
            base_url=os.environ["WANDB_INFERENCE_BASE_URL"],
            api_key=os.environ["WANDB_API_KEY"],
            project=f"{os.environ['WANDB_ENTITY']}/{os.environ['WANDB_PROJECT']}",
        )
    return _client


def chat(messages, tools=None, model=None, max_tokens=1024, temperature=0.7):
    """One chat completion. Returns the raw message (has .content + .tool_calls)."""
    kwargs = dict(
        model=model or DEFAULT_MODEL,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"  
    resp = get_client().chat.completions.create(**kwargs)
    return resp.choices[0].message
