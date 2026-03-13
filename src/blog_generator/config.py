"""Configuration management."""

import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class RetryConfigModel(BaseModel):
    """Retry configuration with sensible defaults."""
    max_attempts: int = Field(default=3, ge=1, le=10)
    base_delay_ms: int = Field(default=1000, ge=100)
    max_delay_ms: int = Field(default=30000, ge=1000)
    rate_limit_delay_ms: int = Field(default=60000, ge=1000)


class ImageConfig(BaseModel):
    """Image generation configuration with Zhipu AI GLM-Image defaults.

    API docs: https://docs.z.ai/guides/image/glm-image
    """
    base_url: str = "https://api.z.ai/api/paas/v4"
    model: str = "glm-image"
    size: str = "1024x1024"


class ApiConfig(BaseModel):
    anthropic_auth_token: str
    anthropic_base_url: str = "https://api.anthropic.com"
    default_model: str = "claude-sonnet-4-6"
    timeout_ms: int = 120000


class Config(BaseModel):
    api: ApiConfig
    github_token: Optional[str] = None
    github_repo_url: str = "https://github.com/vllm-project/vllm-omni"
    default_language: str = "zh"
    retry: RetryConfigModel = Field(default_factory=RetryConfigModel)
    image: ImageConfig = Field(default_factory=ImageConfig)

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
    # Check for local development first, then Docker path
    local_path = Path("blogs/config.json")
    docker_path = Path("/app/blogs/config.json")

    if local_path.exists():
        return Config.load(local_path)
    elif docker_path.exists():
        return Config.load(docker_path)
    else:
        raise FileNotFoundError(
            f"Config file not found. Checked:\n"
            f"  - {local_path.absolute()}\n"
            f"  - {docker_path}\n"
            f"Please create blogs/config.json"
        )


def get_blogs_dir() -> Path:
    """Get the blogs directory path."""
    local_path = Path("blogs")
    docker_path = Path("/app/blogs")
    return local_path if local_path.exists() else docker_path
