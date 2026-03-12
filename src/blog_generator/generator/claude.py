"""Claude API content generator."""

import json
import re
from anthropic import Anthropic
from dataclasses import dataclass

from blog_generator.config import Config
from blog_generator.fetcher.github import Release, Commit, PullRequest, Issue
from blog_generator.fetcher.docs import Doc
from blog_generator.fetcher.images import ImageInput


@dataclass
class BlogDraft:
    title: str
    summary: str
    tags: list[str]
    content: str


class ClaudeGenerator:
    def __init__(self, config: Config):
        self.config = config
        self.timeout = config.api.timeout_ms / 1000  # Convert to seconds
        self.client = Anthropic(
            api_key=config.api.anthropic_auth_token,
            base_url=config.api.anthropic_base_url,
            timeout=self.timeout,
        )
        self.model = config.api.default_model

    def generate_draft(
        self,
        release: Release,
        commits: list[Commit],
        prs: list[PullRequest],
        issues: list[Issue],
        docs: list[Doc],
        images: list[ImageInput] | None = None,
        image_paths: list[tuple[str, str]] | None = None,
        language: str = "zh",
    ) -> BlogDraft:
        """Generate blog draft from collected data."""
        images = images or []
        image_paths = image_paths or []

        # Build context (with size limits for faster API response)
        release_body = self._compact_text(release.body, limit=800)
        commits_summary = self._format_commits(commits[:10])  # Limit to 10 commits
        prs_content = self._format_prs(prs)
        issues_content = self._format_issues(issues)
        docs_content = self._format_docs(docs)

        # Build user prompt (more concise for faster generation)
        image_hint = "\n若提供了图片，请根据图片内容在博客中适当描述或引用（如架构图、截图）。\n\n" if images else ""
        if image_paths:
            paths_str = "、".join(p for p, _ in image_paths)
            image_hint += f"以下图片将保存为以下路径，请在正文合适位置用 markdown 插入图片，例如 ![描述](images/xxx.png)。图片路径列表：{paths_str}\n\n"
        user_prompt = f"""为 vLLM-Omni {release.tag_name} 写一篇技术博客。

版本: {release.tag_name} ({release.published_at[:10]})
更新说明: {release_body}

主要提交:
{commits_summary}

相关PR: {prs_content if prs_content != "无" else "无"}
相关Issue: {issues_content if issues_content != "无" else "无"}
参考文档:
{docs_content}
{image_hint}要求:
- 语言: {"中文" if language == "zh" else "English"}
- 字数: 800-1200字
- 标题有吸引力
- 包含1-2个代码示例
- 优先提炼对用户有价值的变化，不要逐段复述原文
- 只输出合法 JSON，不要加代码块

输出JSON格式:
{{"title": "...", "summary": "...", "tags": [...], "content": "..."}}"""

        content_blocks: list[dict] = [{"type": "text", "text": user_prompt}]
        for img in images:
            content_blocks.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": img.media_type,
                    "data": img.data_base64,
                },
            })

        # Call Claude API
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,  # Reduced for faster generation
            system=self._get_system_prompt(),
            messages=[{"role": "user", "content": content_blocks}],
        )

        # Parse response
        content = response.content[0].text
        return self._parse_response(content)

    def generate_from_prs(
        self,
        prs: list[PullRequest],
        issues: list[Issue],
        docs: list[Doc],
        images: list[ImageInput] | None = None,
        image_paths: list[tuple[str, str]] | None = None,
        language: str = "zh",
    ) -> BlogDraft:
        """Generate blog draft from PRs only (faster, smaller context)."""
        images = images or []
        image_paths = image_paths or []
        prs_content = self._format_prs(prs)
        issues_content = self._format_issues(issues)
        docs_content = self._format_docs(docs)

        # Build concise prompt
        image_hint = "\n若提供了图片，请根据图片内容在博客中适当描述或引用。\n\n" if images else ""
        if image_paths:
            paths_str = "、".join(p for p, _ in image_paths)
            image_hint += f"以下图片将保存为以下路径，请在正文合适位置用 markdown 插入图片，例如 ![描述](images/xxx.png)。图片路径列表：{paths_str}\n\n"
        user_prompt = f"""基于以下PR/Issue写一篇简短的技术介绍。

相关PR:
{prs_content}

相关Issue:
{issues_content}

参考文档:
{docs_content}
{image_hint}要求:
- 语言: {"中文" if language == "zh" else "English"}
- 字数: 300-500字
- 说明改动的作用和价值
- 优先提炼对用户有价值的变化，不要逐段复述原文
- 只输出合法 JSON，不要加代码块

输出JSON格式:
{{"title": "...", "summary": "...", "tags": [...], "content": "..."}}"""

        content_blocks: list[dict] = [{"type": "text", "text": user_prompt}]
        for img in images:
            content_blocks.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": img.media_type,
                    "data": img.data_base64,
                },
            })

        # Call API with shorter timeout
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": content_blocks}],
        )

        content = response.content[0].text
        return self._parse_response(content)

    def _get_system_prompt(self) -> str:
        """Get system prompt for draft generation."""
        return """你是 vLLM-Omni 项目的技术博主，为 AI 爱好者撰写通俗易懂的技术博客。

写作风格：
- 用比喻解释复杂概念
- 多用实例展示功能用途
- 语气友好热情

如果用户提供了图片（如架构图、界面截图），请在文章中适当描述或引用。

文章结构：
1. 开篇：用场景或问题引入
2. 核心更新：列出主要亮点（2-3个）
3. 功能详解：配使用场景
4. 快速上手：简单示例
5. 结尾：鼓励尝试

输出JSON格式，包含 title, summary, tags, content 字段。"""

    def _format_commits(self, commits: list[Commit]) -> str:
        if not commits:
            return "无"
        lines = []
        for c in commits[:10]:  # Limit to 10 commits
            lines.append(f"- [{c.sha}] {c.message} (@{c.author})")
        return "\n".join(lines)

    def _format_prs(self, prs: list[PullRequest]) -> str:
        if not prs:
            return "无"
        lines = []
        for pr in prs:
            summary = self._compact_text(pr.body, limit=280)
            lines.append(f"- PR #{pr.number}: {pr.title}\n  摘要: {summary}")
        return "\n\n".join(lines)

    def _format_issues(self, issues: list[Issue]) -> str:
        if not issues:
            return "无"
        lines = []
        for issue in issues:
            summary = self._compact_text(issue.body, limit=240)
            lines.append(f"- Issue #{issue.number}: {issue.title}\n  摘要: {summary}")
        return "\n\n".join(lines)

    def _format_docs(self, docs: list[Doc]) -> str:
        if not docs:
            return "无"
        lines = []
        for doc in docs:
            summary = self._compact_text(doc.content, limit=600)
            lines.append(f"- {doc.path}\n  关键内容: {summary}")
        return "\n\n".join(lines)

    def _compact_text(self, text: str, limit: int) -> str:
        """Reduce markdown-heavy source text into a compact plain-text summary."""
        if not text:
            return "无"

        compact = re.sub(r"```[\s\S]*?```", " ", text)
        compact = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", compact)
        compact = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", compact)
        compact = re.sub(r"^#{1,6}\s*", "", compact, flags=re.MULTILINE)
        compact = re.sub(r"[*_>`~-]+", " ", compact)
        compact = re.sub(r"\s+", " ", compact).strip()

        if len(compact) <= limit:
            return compact

        truncated = compact[:limit].rsplit(" ", 1)[0].strip()
        return f"{truncated or compact[:limit].strip()}..."

    def _parse_response(self, content: str) -> BlogDraft:
        """Parse JSON response from Claude."""
        # Try to extract JSON from response
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0].strip()
        else:
            # Try to find JSON object in content
            match = re.search(r'\{[\s\S]*\}', content)
            if match:
                json_str = match.group(0)
            else:
                json_str = content.strip()

        # Try to parse JSON
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            # If parsing fails, try to extract fields manually with regex
            print(f"JSON parse error: {e}")
            print(f"Attempting to extract fields manually...")

            title_match = re.search(r'"title"\s*:\s*"([^"]*)"', json_str)
            summary_match = re.search(r'"summary"\s*:\s*"([^"]*)"', json_str)
            tags_match = re.search(r'"tags"\s*:\s*\[([^\]]*)\]', json_str)
            content_match = re.search(r'"content"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', json_str, re.DOTALL)

            data = {
                "title": title_match.group(1) if title_match else "Untitled",
                "summary": summary_match.group(1) if summary_match else "",
                "tags": [],
                "content": content_match.group(1).replace('\\"', '"').replace('\\n', '\n') if content_match else json_str,
            }

            if tags_match:
                tags_str = tags_match.group(1)
                data["tags"] = re.findall(r'"([^"]*)"', tags_str)

        return BlogDraft(
            title=data.get("title", "Untitled"),
            summary=data.get("summary", ""),
            tags=data.get("tags", []),
            content=data.get("content", ""),
        )
