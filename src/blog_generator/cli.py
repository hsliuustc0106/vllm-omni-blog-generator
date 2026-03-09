"""CLI entry point."""

import asyncio
import json
import shutil
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
from blog_generator.formatter.zhihu import ZhihuFormatter
from blog_generator.formatter.xiaohongshu import XiaohongshuFormatter

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


@app.command("list")
def list_blogs() -> None:
    """List all generated blogs."""
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
        shutil.rmtree(output_dir)
        console.print(f"[yellow]Removed existing draft for {release}[/yellow]")

    console.print(f"[cyan]Regenerating {release}...[/cyan]")
    console.print(f"Run: [cyan]blog-generator generate --release {release}[/cyan]")


if __name__ == "__main__":
    app()
