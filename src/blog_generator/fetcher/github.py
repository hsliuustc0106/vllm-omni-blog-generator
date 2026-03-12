"""GitHub API fetcher with retry support."""

import httpx
from typing import Optional
from dataclasses import dataclass

from blog_generator.utils.retry import retry_async, RetryExhaustedError, NotFoundError


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
    head_sha: Optional[str] = None  # for building raw URLs to PR branch content


@dataclass
class Issue:
    number: int
    title: str
    body: str


class GitHubFetcher:
    BASE_URL = "https://api.github.com/repos/vllm-project/vllm-omni"

    def __init__(self, token: Optional[str] = None, max_retries: int = 3):
        self.token = token
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            self.headers["Authorization"] = f"token {token}"
        self.max_retries = max_retries

    async def _get(self, client: httpx.AsyncClient, path: str) -> dict:
        """Make GET request to GitHub API with retry."""

        @retry_async(max_attempts=self.max_retries, base_delay=1.0, max_delay=30.0)
        async def _fetch():
            response = await client.get(f"{self.BASE_URL}{path}", headers=self.headers)
            response.raise_for_status()
            return response.json()

        try:
            return await _fetch()
        except NotFoundError:
            raise
        except RetryExhaustedError as e:
            raise

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
        except NotFoundError:
            raise ValueError(f"Release {tag} not found")

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
        """Get commits on the default branch after the given release tag."""
        data = await self._get(client, f"/compare/{release_tag}...HEAD")

        compare_commits = data.get("commits", [])
        if not compare_commits:
            return []

        # GitHub returns commits oldest -> newest for compare; keep the most recent ones first.
        recent_commits = list(reversed(compare_commits[-limit:]))

        commits = []
        for item in recent_commits:
            sha = item["sha"][:7]
            message = item["commit"]["message"].split("\n")[0]
            author = (
                item.get("author", {}) or {}
            ).get("login") or item["commit"]["author"]["name"]
            commits.append(Commit(sha=sha, message=message, author=author))

        return commits

    async def get_pr(self, client: httpx.AsyncClient, pr_number: int) -> PullRequest:
        """Get PR by number."""
        data = await self._get(client, f"/pulls/{pr_number}")
        head = data.get("head") or {}
        head_sha = head.get("sha")
        return PullRequest(
            number=data["number"],
            title=data["title"],
            body=data["body"] or "",
            merged_at=data.get("merged_at") or "",
            head_sha=head_sha,
        )

    async def get_pr_files(self, client: httpx.AsyncClient, pr_number: int) -> list[dict]:
        """List files changed in a PR. Each dict has 'filename', 'status', etc."""
        data = await self._get(client, f"/pulls/{pr_number}/files")
        return data

    async def get_issue(self, client: httpx.AsyncClient, issue_number: int) -> Issue:
        """Get issue by number."""
        data = await self._get(client, f"/issues/{issue_number}")
        return Issue(
            number=data["number"],
            title=data["title"],
            body=data["body"] or "",
        )
