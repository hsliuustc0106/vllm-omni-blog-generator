"""Configuration management."""

import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel


class ApiConfig(BaseModel):
    anthropic_auth_token: str
    anthropic_base_url: str = "https://api.anthropic.com"
    default_model: str = "claude-sonnet-4-6"
    timeout_ms: int = 120000


class Config(BaseModel):
    api: ApiConfig
    github_token: Optional[str] = None
    default_language: str = "zh"

    @classmethod
    def load(cls, config_path: Path) -> "Config":
        """Load config from JSON file."""
        if not config_path.exists():
            raise FileNotFoundError(
                f"Config file not found: {config_path}\n"
                f"Please create it with:\n"
                f'  {{"api": {{"anthropic_auth_token": "xxx", "anthropic_base_url": "..."}}}}'
            )

        with open(config_path) as f:
            data = json.load(f)

        return cls(**data)


def get_config() -> Config:
    """Get config from default location."""
    config_path = Path("/app/blogs/config.json")
    return Config.load(config_path)
