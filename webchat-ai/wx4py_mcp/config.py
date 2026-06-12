"""Environment-based configuration."""

import os
from dataclasses import dataclass


@dataclass
class Wx4PyConfig:
    ai_base_url: str = ""
    ai_model: str = "glm-4-flash"
    ai_api_key: str = ""
    ai_api_format: str = "completions"
    poll_interval_sec: float = 15.0

    @classmethod
    def from_env(cls) -> "Wx4PyConfig":
        return cls(
            ai_base_url=os.getenv("WX4PY_AI_BASE_URL", ""),
            ai_model=os.getenv("WX4PY_AI_MODEL", "glm-4-flash"),
            ai_api_key=os.getenv("WX4PY_AI_API_KEY", ""),
            ai_api_format=os.getenv("WX4PY_AI_API_FORMAT", "completions"),
            poll_interval_sec=float(os.getenv("WX4PY_POLL_INTERVAL", "15")),
        )
