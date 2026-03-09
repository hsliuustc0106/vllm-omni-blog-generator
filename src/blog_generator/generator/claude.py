"""Claude API content generator."""

import json
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
        import re

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
