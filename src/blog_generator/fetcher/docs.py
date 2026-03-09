"""Documentation fetcher."""

import httpx
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class Doc:
    path: str
    content: str


class DocFetcher:
    GITHUB_RAW_URL = "https://raw.githubusercontent.com/vllm-project/vllm-omni/main"

    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = repo_path

    def is_url(self, path: str) -> bool:
        """Check if path is a URL."""
        return path.startswith("http://") or path.startswith("https://")

    def is_github_url(self, path: str) -> bool:
        """Check if path is a GitHub URL."""
        return "github.com/vllm-project/vllm-omni" in path

    def github_url_to_raw(self, url: str) -> str:
        """Convert GitHub page URL to raw content URL."""
        # Convert: https://github.com/vllm-project/vllm-omni/blob/main/docs/xxx.md
        # To: https://raw.githubusercontent.com/vllm-project/vllm-omni/main/docs/xxx.md
        return url.replace(
            "github.com/vllm-project/vllm-omni/blob/main/",
            "raw.githubusercontent.com/vllm-project/vllm-omni/main/"
        )

    async def fetch(self, client: httpx.AsyncClient, path: str) -> Doc:
        """Fetch doc from URL or local path."""
        if self.is_url(path):
            return await self._fetch_url(client, path)
        else:
            return self._fetch_local(path)

    async def _fetch_url(self, client: httpx.AsyncClient, url: str) -> Doc:
        """Fetch doc from URL."""
        if self.is_github_url(url):
            url = self.github_url_to_raw(url)

        response = await client.get(url)
        response.raise_for_status()

        return Doc(path=url, content=response.text)

    def _fetch_local(self, path: str) -> Doc:
        """Fetch doc from local file."""
        if self.repo_path:
            full_path = self.repo_path / path
        else:
            full_path = Path(path)

        if not full_path.exists():
            raise FileNotFoundError(f"Doc not found: {full_path}")

        content = full_path.read_text()
        return Doc(path=str(full_path), content=content)
