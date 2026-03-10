from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values, load_dotenv


ROOT = Path(__file__).resolve().parents[2]
ENV_CANDIDATES = [
    ROOT / ".env",
    Path("/Users/rajiv.shah/Code/openhands_working/tutorial_openhands_skill_eval/.env"),
]


def load_project_env() -> Path | None:
    project_env = ENV_CANDIDATES[0]
    fallback_env = ENV_CANDIDATES[1]

    loaded: Path | None = None
    if project_env.exists():
        load_dotenv(project_env, override=False)
        loaded = project_env

    if fallback_env.exists():
        # Only inherit secrets and cloud config from the older tutorial repo.
        # Do not inherit LiteLLM proxy settings or model aliases.
        for key in ("OPENHANDS_CLOUD_API_KEY", "LLM_API_KEY", "LMNR_PROJECT_API_KEY"):
            if not os.getenv(key):
                value = dotenv_values(fallback_env).get(key)
                if value:
                    os.environ[key] = value
        if loaded is None:
            loaded = fallback_env

    # The current repo should default to direct OpenHands SDK model routing.
    os.environ.pop("LLM_BASE_URL", None)
    if not os.getenv("LLM_MODEL", "").startswith("openhands/"):
        os.environ["LLM_MODEL"] = "openhands/claude-sonnet-4-5-20250929"

    return loaded


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value
