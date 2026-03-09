# vLLM-Omni Blog Generator Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Docker-based CLI tool that generates technical blog posts for vLLM-Omni releases, targeting Zhihu and Xiaohongshu platforms.

**Architecture:** Python CLI with Typer, fetches data from GitHub API, generates content via Claude API (Zhipu endpoint), outputs multiple formats (Markdown, JSON, platform-specific). Two-phase workflow: generate draft → user edits → publish.

**Tech Stack:** Python 3.11+, Typer, httpx, Anthropic SDK, Pydantic, Docker

---

## Phase 1: Project Setup

### Task 1: Initialize Project Structure

**Files:**
- Create: `pyproject.toml`
- Create: `src/blog_generator/__init__.py`
- Create: `.gitignore`

**Step 1: Create pyproject.toml**

```toml
[project]
name = "blog-generator"
version = "0.1.0"
description = "Generate technical blog posts for vLLM-Omni releases"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "typer>=0.9.0",
    "httpx>=0.27.0",
    "anthropic>=0.25.0",
    "pydantic>=2.0.0",
    "rich>=13.0.0",
]

[project.scripts]
blog-generator = "blog_generator.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Step 2: Create package init**

```python
# src/blog_generator/__init__.py
"""vLLM-Omni Blog Generator."""

__version__ = "0.1.0"
```

**Step 3: Create .gitignore**

```
__pycache__/
*.py[cod]
*$py.class
.venv/
blogs/
*.egg-info/
dist/
.env
```

**Step 4: Commit**

```bash
git init
git add pyproject.toml src/blog_generator/__init__.py .gitignore
git commit -m "chore: initialize project structure"
```

---

### Task 2: Create Dockerfile

**Files:**
- Create: `Dockerfile`

**Step 1: Create Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy source code
COPY src/ src/

# Create blogs directory
RUN mkdir -p /app/blogs

ENTRYPOINT ["python", "-m", "blog_generator.cli"]
```

**Step 2: Commit**

```bash
git add Dockerfile
git commit -m "chore: add Dockerfile"
```

---

### Task 3: Create README

**Files:**
- Create: `README.md`

**Step 1: Create README**

```markdown
# vLLM-Omni Blog Generator

Generate technical blog posts for vLLM-Omni releases, targeting Zhihu and Xiaohongshu.

## Quick Start

```bash
# Build
docker build -t blog-generator .

# Generate blog for latest release
docker run --rm -v ./blogs:/app/blogs blog-generator generate --latest

# Generate blog for specific release with context
docker run --rm -v ./blogs:/app/blogs blog-generator generate \
  --release v0.16.0 \
  --issue 1666 \
  --pr 1197 \
  --doc docs/design/architecture_overview.md

# Edit the generated draft
vim blogs/v0.16.0/blog.md

# Publish to platform formats
docker run --rm -v ./blogs:/app/blogs blog-generator publish --release v0.16.0
```

## Configuration

Create `blogs/config.json`:

```json
{
  "api": {
    "anthropic_auth_token": "your-token",
    "anthropic_base_url": "https://open.bigmodel.cn/api/anthropic",
    "default_model": "glm-5",
    "timeout_ms": 3000000
  },
  "github_token": "ghp_xxx",
  "default_language": "zh"
}
```

## Output Structure

```
blogs/
├── config.json
├── v0.16.0/
│   ├── blog.md              # Editable draft
│   ├── blog.json            # Structured metadata
│   ├── zhihu/
│   │   └── content.md
│   └── xiaohongshu/
│       ├── content.md
│       └── images/
│           └── prompts.md
```
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README"
```

---

## Phase 2: Core Modules

### Task 4: Create Config Module

**Files:**
- Create: `src/blog_generator/config.py`

**Step 1: Create config module**

```python
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
```

**Step 2: Commit**

```bash
git add src/blog_generator/config.py
git commit -m "feat: add config module"
```

---

### Task 5: Create CLI Skeleton

**Files:**
- Create: `src/blog_generator/cli.py`

**Step 1: Create CLI module**

```python
"""CLI entry point."""

import typer
from rich.console import Console

from blog_generator.config import get_config

app = typer.Typer(name="blog-generator", help="Generate technical blog posts for vLLM-Omni")
console = Console()


@app.command()
def generate(
    release: str = typer.Option(None, help="Release version (e.g., v0.16.0)"),
    latest: bool = typer.Option(False, "--latest", help="Use latest release"),
    issue: list[int] = typer.Option([], "--issue", help="GitHub issue number"),
    pr: list[int] = typer.Option([], "--pr", help="GitHub PR number"),
    doc: list[str] = typer.Option([], "--doc", help="Doc path or URL"),
    lang: str = typer.Option(None, help="Language (zh/en)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing"),
) -> None:
    """Generate blog draft for a release."""
    config = get_config()
    language = lang or config.default_language

    if not release and not latest:
        console.print("[red]Error: Specify --release or --latest[/red]")
        raise typer.Exit(1)

    console.print("[yellow]Generate command not yet implemented[/yellow]")
    console.print(f"  Release: {release or 'latest'}")
    console.print(f"  Issues: {issue}")
    console.print(f"  PRs: {pr}")
    console.print(f"  Docs: {doc}")
    console.print(f"  Language: {language}")


@app.command()
def publish(
    release: str = typer.Option(..., help="Release version"),
    platform: str = typer.Option(None, help="Platform (zhihu/xiaohongshu)"),
) -> None:
    """Generate platform-specific versions from approved draft."""
    console.print("[yellow]Publish command not yet implemented[/yellow]")
    console.print(f"  Release: {release}")
    console.print(f"  Platform: {platform or 'all'}")


@app.command()
def list_blogs() -> None:
    """List all generated blogs."""
    console.print("[yellow]List command not yet implemented[/yellow]")


@app.command()
def regenerate(
    release: str = typer.Option(..., help="Release version"),
) -> None:
    """Regenerate draft (overwrites existing)."""
    console.print("[yellow]Regenerate command not yet implemented[/yellow]")
    console.print(f"  Release: {release}")


if __name__ == "__main__":
    app()
```

**Step 2: Commit**

```bash
git add src/blog_generator/cli.py
git commit -m "feat: add CLI skeleton"
```

---

## Phase 3: Fetcher Module

### Task 6: Create Fetcher Package

**Files:**
- Create: `src/blog_generator/fetcher/__init__.py`

**Step 1: Create init file**

```python
"""Data fetcher module."""

from blog_generator.fetcher.github import GitHubFetcher
from blog_generator.fetcher.docs import DocFetcher

__all__ = ["GitHubFetcher", "DocFetcher"]
```

**Step 2: Commit**

```bash
git add src/blog_generator/fetcher/__init__.py
git commit -m "feat: add fetcher package"
```

---

### Task 7: Create GitHub Fetcher

**Files:**
- Create: `src/blog_generator/fetcher/github.py`

**Step 1: Create GitHub fetcher**

```python
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
        self, client: httpx.AsyncClient, release_tag: str, limit: int = 50
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
```

**Step 2: Commit**

```bash
git add src/blog_generator/fetcher/github.py
git commit -m "feat: add GitHub fetcher"
```

---

### Task 8: Create Doc Fetcher

**Files:**
- Create: `src/blog_generator/fetcher/docs.py`

**Step 1: Create doc fetcher**

```python
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
```

**Step 2: Commit**

```bash
git add src/blog_generator/fetcher/docs.py
git commit -m "feat: add doc fetcher"
```

---

## Phase 4: Generator Module

### Task 9: Create Generator Package

**Files:**
- Create: `src/blog_generator/generator/__init__.py`

**Step 1: Create init file**

```python
"""Content generator module."""

from blog_generator.generator.claude import ClaudeGenerator

__all__ = ["ClaudeGenerator"]
```

**Step 2: Commit**

```bash
git add src/blog_generator/generator/__init__.py
git commit -m "feat: add generator package"
```

---

### Task 10: Create Claude Generator

**Files:**
- Create: `src/blog_generator/generator/claude.py`

**Step 1: Create Claude generator**

```python
"""Claude API content generator."""

from anthropic import Anthropic
from dataclasses import dataclass

from blog_generator.config import Config
from blog_generator.fetcher.github import Release, Commit, PullRequest, Issue
from blog_generator.fetcher.docs import Doc


@dataclass
class BlogDraft:
    title: str
    summary: str
    tags: list[str]
    content: str


class ClaudeGenerator:
    def __init__(self, config: Config):
        self.config = config
        self.client = Anthropic(
            api_key=config.api.anthropic_auth_token,
            base_url=config.api.anthropic_base_url,
        )
        self.model = config.api.default_model
        self.timeout = config.api.timeout_ms / 1000  # Convert to seconds

    def generate_draft(
        self,
        release: Release,
        commits: list[Commit],
        prs: list[PullRequest],
        issues: list[Issue],
        docs: list[Doc],
        language: str = "zh",
    ) -> BlogDraft:
        """Generate blog draft from collected data."""

        # Build context
        commits_summary = self._format_commits(commits)
        prs_content = self._format_prs(prs)
        issues_content = self._format_issues(issues)
        docs_content = self._format_docs(docs)

        # Build user prompt
        user_prompt = f"""请为 vLLM-Omni {release.tag_name} 版本撰写一篇技术博客。

## 版本信息
- 版本号: {release.tag_name}
- 发布日期: {release.published_at[:10]}
- 发布说明: {release.body}

## 本次更新的主要提交
{commits_summary}

## 相关 PR
{prs_content}

## 相关 Issue
{issues_content}

## 参考文档
{docs_content}

## 要求
- 语言：{"中文" if language == "zh" else "English"}
- 字数：1500-2500字
- 标题要有吸引力
- 包含2-3个代码示例

请以JSON格式输出：
{{"title": "...", "summary": "...", "tags": [...], "content": "..."}}"""

        # Call Claude API
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=self._get_system_prompt(),
            messages=[{"role": "user", "content": user_prompt}],
            timeout=self.timeout,
        )

        # Parse response
        content = response.content[0].text
        return self._parse_response(content)

    def _get_system_prompt(self) -> str:
        """Get system prompt for draft generation."""
        return """你是 vLLM-Omni 项目的技术博主。你为大众 AI 爱好者撰写技术博客，语言通俗易懂，重点介绍新功能的能力和应用场景，而非深奥的技术细节。

写作风格：
- 用生动的比喻解释复杂概念
- 多用实例展示功能用途
- 避免过多专业术语，必要时用简单语言解释
- 语气友好、热情，像在给朋友介绍新玩具
- 适当使用emoji增加可读性（但不过度）

文章结构：
1. 开篇：用一个吸引人的场景或问题引入
2. 核心更新：列出本次版本的主要亮点（3-5个）
3. 功能详解：每个亮点配一个使用场景
4. 性能提升：用通俗语言描述性能改进
5. 快速上手：给出一个简单的使用示例
6. 结尾：鼓励读者尝试，提供文档链接

输出格式：JSON，包含 title, summary, tags, content 字段。"""

    def _format_commits(self, commits: list[Commit]) -> str:
        if not commits:
            return "无"
        lines = []
        for c in commits[:20]:  # Limit to 20 commits
            lines.append(f"- [{c.sha}] {c.message} (@{c.author})")
        return "\n".join(lines)

    def _format_prs(self, prs: list[PullRequest]) -> str:
        if not prs:
            return "无"
        lines = []
        for pr in prs:
            lines.append(f"### PR #{pr.number}: {pr.title}\n{pr.body[:500]}")
        return "\n\n".join(lines)

    def _format_issues(self, issues: list[Issue]) -> str:
        if not issues:
            return "无"
        lines = []
        for issue in issues:
            lines.append(f"### Issue #{issue.number}: {issue.title}\n{issue.body[:500]}")
        return "\n\n".join(lines)

    def _format_docs(self, docs: list[Doc]) -> str:
        if not docs:
            return "无"
        lines = []
        for doc in docs:
            lines.append(f"### {doc.path}\n{doc.content[:2000]}")
        return "\n\n".join(lines)

    def _parse_response(self, content: str) -> BlogDraft:
        """Parse JSON response from Claude."""
        import json

        # Try to extract JSON from response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        data = json.loads(content.strip())
        return BlogDraft(
            title=data["title"],
            summary=data["summary"],
            tags=data["tags"],
            content=data["content"],
        )
```

**Step 2: Commit**

```bash
git add src/blog_generator/generator/claude.py
git commit -m "feat: add Claude generator"
```

---

## Phase 5: Formatter Module

### Task 11: Create Formatter Package

**Files:**
- Create: `src/blog_generator/formatter/__init__.py`

**Step 1: Create init file**

```python
"""Output formatter module."""

from blog_generator.formatter.markdown import MarkdownFormatter
from blog_generator.formatter.json_fmt import JsonFormatter
from blog_generator.formatter.zhihu import ZhihuFormatter
from blog_generator.formatter.xiaohongshu import XiaohongshuFormatter

__all__ = ["MarkdownFormatter", "JsonFormatter", "ZhihuFormatter", "XiaohongshuFormatter"]
```

**Step 2: Commit**

```bash
git add src/blog_generator/formatter/__init__.py
git commit -m "feat: add formatter package"
```

---

### Task 12: Create Markdown Formatter

**Files:**
- Create: `src/blog_generator/formatter/markdown.py`

**Step 1: Create markdown formatter**

```python
"""Markdown output formatter."""

from pathlib import Path
from datetime import datetime

from blog_generator.generator.claude import BlogDraft
from blog_generator.fetcher.github import Release


class MarkdownFormatter:
    @staticmethod
    def save(draft: BlogDraft, release: Release, output_path: Path) -> None:
        """Save blog as markdown file."""
        content = f"""# {draft.title}

> **版本**: {release.tag_name}
> **发布日期**: {release.published_at[:10]}
> **标签**: {', '.join(draft.tags)}

## 摘要

{draft.summary}

---

{draft.content}

---

*Generated by vLLM-Omni Blog Generator at {datetime.now().isoformat()}*
"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content)
```

**Step 2: Commit**

```bash
git add src/blog_generator/formatter/markdown.py
git commit -m "feat: add markdown formatter"
```

---

### Task 13: Create JSON Formatter

**Files:**
- Create: `src/blog_generator/formatter/json_fmt.py`

**Step 1: Create JSON formatter**

```python
"""JSON output formatter."""

import json
from pathlib import Path
from datetime import datetime
from typing import List

from blog_generator.generator.claude import BlogDraft
from blog_generator.fetcher.github import Release


class JsonFormatter:
    @staticmethod
    def save(
        draft: BlogDraft,
        release: Release,
        source_commits: List[str],
        source_prs: List[int],
        output_path: Path,
    ) -> None:
        """Save blog as JSON file."""
        data = {
            "version": release.tag_name,
            "release_date": release.published_at[:10],
            "language": "zh",
            "title": draft.title,
            "summary": draft.summary,
            "tags": draft.tags,
            "content_md": draft.content,
            "generated_at": datetime.now().isoformat(),
            "source_commits": source_commits,
            "source_prs": source_prs,
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
```

**Step 2: Commit**

```bash
git add src/blog_generator/formatter/json_fmt.py
git commit -m "feat: add JSON formatter"
```

---

### Task 14: Create Zhihu Formatter

**Files:**
- Create: `src/blog_generator/formatter/zhihu.py`

**Step 1: Create Zhihu formatter**

```python
"""Zhihu platform formatter."""

from pathlib import Path
from datetime import datetime


class ZhihuFormatter:
    @staticmethod
    def format(content_md: str, title: str) -> str:
        """Format content for Zhihu."""
        # Add Zhihu-specific formatting
        formatted = f"""# {title}

{content_md}

---

**相关链接**
- [vLLM-Omni GitHub](https://github.com/vllm-project/vllm-omni)
- [vLLM-Omni 文档](https://vllm-omni.readthedocs.io)

*发布于 {datetime.now().strftime('%Y年%m月%d日')}*
"""
        return formatted

    @staticmethod
    def save(content: str, output_path: Path) -> None:
        """Save Zhihu-formatted content."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content)
```

**Step 2: Commit**

```bash
git add src/blog_generator/formatter/zhihu.py
git commit -m "feat: add Zhihu formatter"
```

---

### Task 15: Create Xiaohongshu Formatter

**Files:**
- Create: `src/blog_generator/formatter/xiaohongshu.py`

**Step 1: Create Xiaohongshu formatter**

```python
"""Xiaohongshu platform formatter."""

from pathlib import Path
from datetime import datetime


class XiaohongshuFormatter:
    @staticmethod
    def format(content_md: str, title: str, tags: list[str]) -> tuple[str, str]:
        """Format content for Xiaohongshu.

        Returns:
            tuple: (content, image_prompts)
        """
        # Extract key points for short format
        lines = content_md.split("\n")

        # Build short content (max 800 chars)
        short_content = f"""🔥 {title}

"""
        # Extract first few paragraphs
        char_count = len(short_content)
        for line in lines:
            if line.strip() and not line.startswith("#"):
                if char_count + len(line) > 700:
                    break
                short_content += line + "\n"
                char_count += len(line) + 1

        # Add engagement
        short_content += """
💬 你最期待哪个功能？评论区聊聊！

"""
        # Add hashtags
        hashtag_str = " ".join(f"#{tag}" for tag in tags[:5])
        short_content += hashtag_str

        # Generate image prompts
        image_prompts = f"""# Xiaohongshu Cover Image Prompts

## Cover Image Prompt
Generate a cover image for a technical blog post about vLLM-Omni {title}.

Style: Tech/minimalist, clean background
Text: {title[:20]}
Colors: Blue and white (tech feel)
Elements: AI, multimodal, cloud icons

## Carousel Images (Optional)

### Slide 1: Title
Text: {title}
Background: Gradient blue

### Slide 2: Key Features
List 3-4 main features from the blog

### Slide 3: Code Example
Show a simple usage code snippet

### Slide 4: Call to Action
"关注获取更多 AI 技术分享"
"""

        return short_content, image_prompts

    @staticmethod
    def save(content: str, image_prompts: str, output_dir: Path) -> None:
        """Save Xiaohongshu content and image prompts."""
        output_dir.mkdir(parents=True, exist_ok=True)

        content_path = output_dir / "content.md"
        content_path.write_text(content)

        prompts_path = output_dir / "images" / "prompts.md"
        prompts_path.parent.mkdir(parents=True, exist_ok=True)
        prompts_path.write_text(image_prompts)
```

**Step 2: Commit**

```bash
git add src/blog_generator/formatter/xiaohongshu.py
git commit -m "feat: add Xiaohongshu formatter"
```

---

## Phase 6: Wire Up CLI

### Task 16: Implement Generate Command

**Files:**
- Modify: `src/blog_generator/cli.py`

**Step 1: Implement generate command**

```python
"""CLI entry point."""

from pathlib import Path
from typing import Optional

import httpx
import typer
from rich.console import Console

from blog_generator.config import get_config, Config
from blog_generator.fetcher.github import GitHubFetcher
from blog_generator.fetcher.docs import DocFetcher
from blog_generator.generator.claude import ClaudeGenerator
from blog_generator.formatter.markdown import MarkdownFormatter
from blog_generator.formatter.json_fmt import JsonFormatter

app = typer.Typer(name="blog-generator", help="Generate technical blog posts for vLLM-Omni")
console = Console()

BLOGS_DIR = Path("/app/blogs")


@app.command()
def generate(
    release: str = typer.Option(None, help="Release version (e.g., v0.16.0)"),
    latest: bool = typer.Option(False, "--latest", help="Use latest release"),
    issue: list[int] = typer.Option([], "--issue", help="GitHub issue number"),
    pr: list[int] = typer.Option([], "--pr", help="GitHub PR number"),
    doc: list[str] = typer.Option([], "--doc", help="Doc path or URL"),
    lang: str = typer.Option(None, help="Language (zh/en)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing"),
) -> None:
    """Generate blog draft for a release."""
    config = get_config()
    language = lang or config.default_language

    if not release and not latest:
        console.print("[red]Error: Specify --release or --latest[/red]")
        raise typer.Exit(1)

    import asyncio
    asyncio.run(_generate_async(config, release, latest, issue, pr, doc, language, dry_run))


async def _generate_async(
    config: Config,
    release: Optional[str],
    latest: bool,
    issues: list[int],
    prs: list[int],
    docs: list[str],
    language: str,
    dry_run: bool,
) -> None:
    """Async implementation of generate command."""
    github = GitHubFetcher(config.github_token)
    doc_fetcher = DocFetcher()
    generator = ClaudeGenerator(config)

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Fetch release info
        if latest:
            console.print("[cyan]Fetching latest release...[/cyan]")
            release_info = await github.get_latest_release(client)
        else:
            console.print(f"[cyan]Fetching release {release}...[/cyan]")
            release_info = await github.get_release(client, release)

        console.print(f"[green]✓[/green] Found release: {release_info.tag_name}")

        # Fetch commits
        console.print("[cyan]Fetching commits...[/cyan]")
        commits = await github.get_commits_since_release(client, release_info.tag_name)
        console.print(f"[green]✓[/green] Found {len(commits)} commits")

        # Fetch PRs
        pr_data = []
        for pr_num in prs:
            console.print(f"[cyan]Fetching PR #{pr_num}...[/cyan]")
            pr_data.append(await github.get_pr(client, pr_num))
        console.print(f"[green]✓[/green] Fetched {len(pr_data)} PRs")

        # Fetch issues
        issue_data = []
        for issue_num in issues:
            console.print(f"[cyan]Fetching issue #{issue_num}...[/cyan]")
            issue_data.append(await github.get_issue(client, issue_num))
        console.print(f"[green]✓[/green] Fetched {len(issue_data)} issues")

        # Fetch docs
        doc_data = []
        for doc_path in docs:
            console.print(f"[cyan]Fetching doc: {doc_path}...[/cyan]")
            try:
                doc_data.append(await doc_fetcher.fetch(client, doc_path))
            except Exception as e:
                console.print(f"[yellow]⚠[/yellow] Skip doc {doc_path}: {e}")
        console.print(f"[green]✓[/green] Fetched {len(doc_data)} docs")

        # Generate blog
        console.print("[cyan]Generating blog content...[/cyan]")
        draft = generator.generate_draft(
            release=release_info,
            commits=commits,
            prs=pr_data,
            issues=issue_data,
            docs=doc_data,
            language=language,
        )
        console.print(f"[green]✓[/green] Generated: {draft.title}")

        if dry_run:
            console.print("\n[bold]--- DRAFT PREVIEW ---[/bold]\n")
            console.print(f"Title: {draft.title}")
            console.print(f"Summary: {draft.summary}")
            console.print(f"Tags: {draft.tags}")
            console.print(f"\n{draft.content[:500]}...")
            return

        # Save outputs
        output_dir = BLOGS_DIR / release_info.tag_name
        output_dir.mkdir(parents=True, exist_ok=True)

        MarkdownFormatter.save(draft, release_info, output_dir / "blog.md")
        console.print(f"[green]✓[/green] Saved: {output_dir}/blog.md")

        JsonFormatter.save(
            draft,
            release_info,
            [c.sha for c in commits],
            prs,
            output_dir / "blog.json",
        )
        console.print(f"[green]✓[/green] Saved: {output_dir}/blog.json")

        console.print(f"\n[bold green]✓ Blog generated successfully![/bold green]")
        console.print(f"  Draft: {output_dir}/blog.md")
        console.print(f"  Edit the draft, then run:")
        console.print(f"  [cyan]blog-generator publish --release {release_info.tag_name}[/cyan]")


@app.command()
def publish(
    release: str = typer.Option(..., help="Release version"),
    platform: str = typer.Option(None, help="Platform (zhihu/xiaohongshu)"),
) -> None:
    """Generate platform-specific versions from approved draft."""
    from blog_generator.formatter.zhihu import ZhihuFormatter
    from blog_generator.formatter.xiaohongshu import XiaohongshuFormatter
    import json

    output_dir = BLOGS_DIR / release

    if not (output_dir / "blog.md").exists():
        console.print(f"[red]Error: No draft found for {release}[/red]")
        console.print(f"Run: blog-generator generate --release {release}")
        raise typer.Exit(1)

    # Read draft
    with open(output_dir / "blog.json") as f:
        blog_data = json.load(f)

    title = blog_data["title"]
    content = blog_data["content_md"]
    tags = blog_data["tags"]

    # Create approved marker
    (output_dir / "approved").touch()

    # Generate platform versions
    if platform is None or platform == "zhihu":
        zhihu_content = ZhihuFormatter.format(content, title)
        ZhihuFormatter.save(zhihu_content, output_dir / "zhihu" / "content.md")
        console.print(f"[green]✓[/green] Generated: {output_dir}/zhihu/content.md")

    if platform is None or platform == "xiaohongshu":
        xhs_content, image_prompts = XiaohongshuFormatter.format(content, title, tags)
        XiaohongshuFormatter.save(xhs_content, image_prompts, output_dir / "xiaohongshu")
        console.print(f"[green]✓[/green] Generated: {output_dir}/xiaohongshu/content.md")
        console.print(f"[green]✓[/green] Generated: {output_dir}/xiaohongshu/images/prompts.md")

    console.print(f"\n[bold green]✓ Published successfully![/bold green]")
    console.print(f"  Zhihu: {output_dir}/zhihu/content.md")
    console.print(f"  Xiaohongshu: {output_dir}/xiaohongshu/content.md")
    console.print(f"\nTo generate XHS images, run:")
    console.print(f"  [cyan]/baoyu-xhs-images {output_dir}/xiaohongshu/images/prompts.md --style tech[/cyan]")


@app.command()
def list_blogs() -> None:
    """List all generated blogs."""
    import json

    if not BLOGS_DIR.exists():
        console.print("[yellow]No blogs generated yet[/yellow]")
        return

    console.print("[bold]Generated Blogs:[/bold]\n")
    for version_dir in sorted(BLOGS_DIR.iterdir()):
        if version_dir.is_dir() and (version_dir / "blog.json").exists():
            with open(version_dir / "blog.json") as f:
                data = json.load(f)
            status = "[green]approved[/green]" if (version_dir / "approved").exists() else "[yellow]draft[/yellow]"
            console.print(f"  {version_dir.name}: {data['title']} ({status})")


@app.command()
def regenerate(
    release: str = typer.Option(..., help="Release version"),
) -> None:
    """Regenerate draft (overwrites existing)."""
    output_dir = BLOGS_DIR / release

    if output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)
        console.print(f"[yellow]Removed existing draft for {release}[/yellow]")

    # Run generate
    console.print(f"[cyan]Regenerating {release}...[/cyan]")
    # Note: In production, this would call generate() directly
    console.print(f"Run: [cyan]blog-generator generate --release {release}[/cyan]")


if __name__ == "__main__":
    app()
```

**Step 2: Commit**

```bash
git add src/blog_generator/cli.py
git commit -m "feat: implement CLI commands"
```

---

## Phase 7: Finalize

### Task 17: Update Package Structure

**Files:**
- Modify: `pyproject.toml`

**Step 1: Update pyproject.toml for src layout**

```toml
[project]
name = "blog-generator"
version = "0.1.0"
description = "Generate technical blog posts for vLLM-Omni releases"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "typer>=0.9.0",
    "httpx>=0.27.0",
    "anthropic>=0.25.0",
    "pydantic>=2.0.0",
    "rich>=13.0.0",
]

[project.scripts]
blog-generator = "blog_generator.cli:app"

[tool.hatch.build.targets.wheel]
packages = ["src/blog_generator"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Step 2: Commit**

```bash
git add pyproject.toml
git commit -m "chore: update pyproject.toml for src layout"
```

---

### Task 18: Final Commit and Push

**Step 1: Review all files**

```bash
git status
```

**Step 2: Push to GitHub**

```bash
git remote add origin https://github.com/vllm-project/vllm-omni-blog-generator.git
git branch -M main
git push -u origin main
```

---

## Summary

| Phase | Tasks | Description |
|-------|-------|-------------|
| 1 | 1-3 | Project setup (pyproject, Docker, README) |
| 2 | 4-5 | Core modules (config, CLI skeleton) |
| 3 | 6-8 | Fetcher module (GitHub, docs) |
| 4 | 9-10 | Generator module (Claude API) |
| 5 | 11-15 | Formatter module (md, json, zhihu, xiaohongshu) |
| 6 | 16 | Wire up CLI commands |
| 7 | 17-18 | Finalize and push |

**Total: 18 tasks**
