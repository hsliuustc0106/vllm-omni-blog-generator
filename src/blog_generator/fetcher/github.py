"""GitHub API fetcher."""

import httpx
from typing import Optional
from dataclasses import dataclass


@dataclass
class Release:
    tag_name: str
    name: str
    body: str
    published_at: str


@dataclass
class Commit:
    sha: str
    message: str
    author: str


@dataclass
class PullRequest:
    number: int
    title: str
    body: str
    merged_at: str


@dataclass
class Issue:
    number: int
    title: str
    body: str


class GitHubFetcher:
    BASE_URL = "https://api.github.com/repos/vllm-project/vllm-omni"

    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            self.headers["Authorization"] = f"token {token}"

    async def _get(self, client: httpx.AsyncClient, path: str) -> dict:
        """Make GET request to GitHub API."""
        response = await client.get(f"{self.BASE_URL}{path}", headers=self.headers)
        response.raise_for_status()
        return response.json()

    async def get_release(self, client: httpx.AsyncClient, tag: str) -> Release:
        """Get release by tag."""
        try:
            data = await self._get(client, f"/releases/tags/{tag}")
            return Release(
                tag_name=data["tag_name"],
                name=data["name"],
                body=data["body"],
                published_at=data["published_at"],
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(f"Release {tag} not found")
            raise

    async def get_latest_release(self, client: httpx.AsyncClient) -> Release:
        """Get latest release."""
        data = await self._get(client, "/releases/latest")
        return Release(
            tag_name=data["tag_name"],
            name=data["name"],
            body=data["body"],
            published_at=data["published_at"],
        )

    async def get_commits_since_release(
        self, client: httpx.AsyncClient, release_tag: str, limit: int = 10
    ) -> list[Commit]:
        """Get commits since a release."""
        # Get commits on main branch
        data = await self._get(client, f"/commits?per_page={limit}")

        commits = []
        for item in data:
            sha = item["sha"][:7]
            message = item["commit"]["message"].split("\n")[0]
            author = item["commit"]["author"]["name"]
            commits.append(Commit(sha=sha, message=message, author=author))

        return commits

    async def get_pr(self, client: httpx.AsyncClient, pr_number: int) -> PullRequest:
        """Get PR by number."""
        data = await self._get(client, f"/pulls/{pr_number}")
        return PullRequest(
            number=data["number"],
            title=data["title"],
            body=data["body"] or "",
            merged_at=data.get("merged_at") or "",
        )

    async def get_issue(self, client: httpx.AsyncClient, issue_number: int) -> Issue:
        """Get issue by number."""
        data = await self._get(client, f"/issues/{issue_number}")
        return Issue(
            number=data["number"],
            title=data["title"],
            body=data["body"] or "",
        )
