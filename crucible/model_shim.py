"""Pointing agents under test at a local model.

Most open-source agents talk to OpenAI through the official client, which honours
OPENAI_BASE_URL. Ollama serves an OpenAI-compatible API at /v1. Pointing one at
the other is the whole reason this project can run thousands of experiments at
no marginal cost, and it also pins the model as an experimental variable rather
than leaving it a drifting dependency of whoever's API we would otherwise call.

What this deliberately does NOT do is fabricate credentials it cannot satisfy.
An agent that needs a real GitHub token cannot be exercised honestly here, and
`unsatisfiable` names it so the dataset records why rather than reporting a
failure whose cause is a fake token.
"""
from __future__ import annotations

from dataclasses import dataclass

# Credentials a local OpenAI-compatible endpoint can stand in for.
_SHIMMABLE = {"OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_BASE_URL",
              "OPENAI_API_BASE", "OPENAI_MODEL"}


@dataclass(frozen=True)
class ShimConfig:
    base_url: str
    model: str
    api_key: str = "crucible-local"


def shim_env(cfg: ShimConfig) -> dict[str, str]:
    """Environment that redirects a container's model client to the local endpoint.

    Emitted unconditionally rather than only for declared variables: agents
    frequently read a base URL they never declare, and an unset base URL means a
    silent call to the real api.openai.com with a junk key, which is a failed
    experiment that looks like an agent defect.

    It takes no list of declared variables for that reason. It used to, unused,
    because the declared list looked as though it belonged here; it belongs to
    `unsatisfiable`, which is now wired into the check stage and is the only
    caller that has any use for it.
    """
    return {
        "OPENAI_BASE_URL": cfg.base_url,
        "OPENAI_API_BASE": cfg.base_url,
        "OPENAI_API_KEY": cfg.api_key,
        "OPENAI_MODEL": cfg.model,
        "ANTHROPIC_BASE_URL": cfg.base_url,
        "ANTHROPIC_API_KEY": cfg.api_key,
    }


def unsatisfiable(declared: list[str]) -> list[str]:
    """Declared credentials a local shim cannot honestly provide."""
    return [name for name in declared if name.upper() not in _SHIMMABLE]
