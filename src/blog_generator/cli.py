"""CLI entry point."""

import asyncio
import base64
import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import httpx
import typer
from rich.console import Console

from blog_generator.config import get_config, get_blogs_dir, Config
from blog_generator.fetcher.github import GitHubFetcher
from blog_generator.fetcher.docs import DocFetcher
from blog_generator.fetcher.images import (
    ImageInput,
    load_image,
    extract_image_urls_from_markdown,
    image_paths_for_embed,
)
from blog_generator.generator.claude import ClaudeGenerator
from blog_generator.formatter.markdown import MarkdownFormatter
from blog_generator.formatter.json_fmt import JsonFormatter
from blog_generator.formatter.zhihu import ZhihuFormatter
from blog_generator.formatter.xiaohongshu import XiaohongshuFormatter
from blog_generator.utils.retry import NotFoundError, RetryExhaustedError
from blog_generator.publisher.xiaohongshu import (
    XhsPublisher,
    XhsPostData,
    ChromeNotRunningError,
)

app = typer.Typer(name="blog-generator", help="Generate technical blog posts for vLLM-Omni")
console = Console()


@dataclass
class FetchSummary:
    """Track fetch results for summary output."""
    release_fetched: bool = False
    release_error: str = ""
    commits_count: int = 0
    prs_success: list[int] = field(default_factory=list)
    prs_failed: list[tuple[int, str]] = field(default_factory=list)
    issues_success: list[int] = field(default_factory=list)
    issues_failed: list[tuple[int, str]] = field(default_factory=list)
    docs_success: list[str] = field(default_factory=list)
    docs_failed: list[tuple[str, str]] = field(default_factory=list)
    images_success: int = 0
    images_failed: int = 0

    def print_summary(self, output_dir: Path) -> None:
        """Print fetch summary."""
        console.print(f"\n[bold]Blog generated: {output_dir}/blog.md[/bold]\n")
        console.print("[bold]Sources used:[/bold]")

        if self.release_fetched:
            console.print(f"  [green]✓[/green] Release")
        elif self.release_error:
            console.print(f"  [red]✗[/red] Release: {self.release_error}")

        if self.commits_count > 0:
            console.print(f"  [green]✓[/green] {self.commits_count} commits")

        if self.prs_success:
            console.print(f"  [green]✓[/green] {len(self.prs_success)}/{len(self.prs_success) + len(self.prs_failed)} PRs ({', '.join(f'#{n}' for n in self.prs_success)})")
        for pr_num, err in self.prs_failed:
            console.print(f"  [yellow]⚠[/yellow] PR #{pr_num} skipped: {err}")

        if self.issues_success:
            console.print(f"  [green]✓[/green] {len(self.issues_success)}/{len(self.issues_success) + len(self.issues_failed)} issues")
        for iss_num, err in self.issues_failed:
            console.print(f"  [yellow]⚠[/yellow] Issue #{iss_num} skipped: {err}")

        if self.docs_success:
            console.print(f"  [green]✓[/green] {len(self.docs_success)}/{len(self.docs_success) + len(self.docs_failed)} docs")
        for doc_path, err in self.docs_failed:
            console.print(f"  [yellow]⚠[/yellow] Doc skipped ({doc_path}): {err}")

        if self.images_success > 0:
            console.print(f"  [green]✓[/green] {self.images_success} images")
        if self.images_failed > 0:
            console.print(f"  [yellow]⚠[/yellow] {self.images_failed} images skipped")


def get_blogs_dir_path() -> Path:
    """Get blogs directory path (cached per command)."""
    return get_blogs_dir()


@app.command()
def generate(
    release: str = typer.Option(None, help="Release version (e.g., v0.16.0)"),
    latest: bool = typer.Option(False, "--latest", help="Use latest release"),
    issue: list[int] = typer.Option([], "--issue", help="GitHub issue number"),
    pr: list[int] = typer.Option([], "--pr", help="GitHub PR number"),
    doc: list[str] = typer.Option([], "--doc", help="Doc path or URL"),
    image: list[str] = typer.Option([], "--image", "-i", help="Image path or URL (repeatable)"),
    lang: str = typer.Option(None, help="Language (zh/en)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing"),
) -> None:
    """Generate blog draft for a release or from PRs/issues."""
    config = get_config()
    language = lang or config.default_language

    if not release and not latest and not pr and not issue:
        console.print("[red]Error: Specify --release, --latest, --pr, or --issue[/red]")
        raise typer.Exit(1)

    asyncio.run(_generate_async(config, release, latest, issue, pr, doc, image, language, dry_run))


async def _generate_async(
    config: Config,
    release: Optional[str],
    latest: bool,
    issues: list[int],
    prs: list[int],
    docs: list[str],
    image: list[str],
    language: str,
    dry_run: bool,
) -> None:
    """Async implementation of generate command with graceful degradation."""
    github = GitHubFetcher(config.github_token)
    doc_fetcher = DocFetcher()
    generator = ClaudeGenerator(config)
    summary = FetchSummary()

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Check if we have a release or just PRs/issues
        has_release = release or latest

        release_info = None
        commits = []

        if has_release:
            # Fetch release info (hard fail if missing)
            try:
                if latest:
                    console.print("[cyan]Fetching latest release...[/cyan]")
                    release_info = await github.get_latest_release(client)
                else:
                    console.print(f"[cyan]Fetching release {release}...[/cyan]")
                    release_info = await github.get_release(client, release)
                summary.release_fetched = True
                console.print(f"[green]✓[/green] Found release: {release_info.tag_name}")
            except NotFoundError as e:
                summary.release_error = f"Not found: {e}"
                console.print(f"[red]Error: Release not found[/red]")
                raise typer.Exit(1)
            except RetryExhaustedError as e:
                summary.release_error = str(e.last_error)
                console.print(f"[red]Error: {e}[/red]")
                raise typer.Exit(1)

            # Fetch commits (optional)
            try:
                console.print("[cyan]Fetching commits...[/cyan]")
                commits = await github.get_commits_since_release(client, release_info.tag_name)
                summary.commits_count = len(commits)
                console.print(f"[green]✓[/green] Found {len(commits)} commits")
            except (NotFoundError, RetryExhaustedError, httpx.HTTPError) as e:
                console.print(f"[yellow]⚠[/yellow] Could not fetch commits: {e}")

        # Fetch PRs (graceful - skip failures)
        pr_data = []
        for pr_num in prs:
            console.print(f"[cyan]Fetching PR #{pr_num}...[/cyan]")
            try:
                pr_data.append(await github.get_pr(client, pr_num))
                summary.prs_success.append(pr_num)
            except NotFoundError as e:
                summary.prs_failed.append((pr_num, "not found"))
                console.print(f"[yellow]⚠[/yellow] PR #{pr_num} not found, skipping")
            except RetryExhaustedError as e:
                summary.prs_failed.append((pr_num, str(e.last_error)[:50]))
                console.print(f"[yellow]⚠[/yellow] PR #{pr_num} failed after retries, skipping")
        if pr_data:
            console.print(f"[green]✓[/green] Fetched {len(pr_data)}/{len(prs)} PRs")

        # Fetch issues (graceful - skip failures)
        issue_data = []
        for issue_num in issues:
            console.print(f"[cyan]Fetching issue #{issue_num}...[/cyan]")
            try:
                issue_data.append(await github.get_issue(client, issue_num))
                summary.issues_success.append(issue_num)
            except NotFoundError as e:
                summary.issues_failed.append((issue_num, "not found"))
                console.print(f"[yellow]⚠[/yellow] Issue #{issue_num} not found, skipping")
            except RetryExhaustedError as e:
                summary.issues_failed.append((issue_num, str(e.last_error)[:50]))
                console.print(f"[yellow]⚠[/yellow] Issue #{issue_num} failed after retries, skipping")
        if issue_data:
            console.print(f"[green]✓[/green] Fetched {len(issue_data)}/{len(issues)} issues")

        # Fetch docs (graceful - skip failures)
        doc_data = []
        for doc_path in docs:
            console.print(f"[cyan]Fetching doc: {doc_path}...[/cyan]")
            try:
                doc_data.append(await doc_fetcher.fetch(client, doc_path))
                summary.docs_success.append(doc_path)
            except Exception as e:
                summary.docs_failed.append((doc_path, str(e)[:50]))
                console.print(f"[yellow]⚠[/yellow] Skip doc {doc_path}: {e}")
        if doc_data:
            console.print(f"[green]✓[/green] Fetched {len(doc_data)}/{len(docs)} docs")

        # Collect image sources: user-provided --image, PR/issue body markdown, and PR file list
        image_sources: list[str] = list(image)
        for pr in pr_data:
            image_sources.extend(extract_image_urls_from_markdown(pr.body))
        for iss in issue_data:
            image_sources.extend(extract_image_urls_from_markdown(iss.body))
        # Add image files from PR diffs (e.g. docs/*.png added in the PR)
        for pr in pr_data:
            if pr.head_sha:
                try:
                    files = await github.get_pr_files(client, pr.number)
                    for f in files:
                        filename = (f.get("filename") or "").lower()
                        if any(filename.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp")):
                            raw_url = f"https://raw.githubusercontent.com/vllm-project/vllm-omni/{pr.head_sha}/{f.get('filename')}"
                            image_sources.append(raw_url)
                except Exception as e:
                    console.print(f"[yellow]⚠[/yellow] Could not list PR #{pr.number} files: {e}")
        # Dedupe while preserving order (user images first, then PR/issue images)
        seen_sources = set()
        image_sources_deduped = []
        for src in image_sources:
            if src not in seen_sources:
                seen_sources.add(src)
                image_sources_deduped.append(src)

        # Load images (paths or URLs)
        image_data: list[ImageInput] = []
        if image_sources_deduped:
            for img_src in image_sources_deduped:
                console.print(f"[cyan]Loading image: {img_src}...[/cyan]")
                try:
                    loaded = await load_image(img_src, client)
                    image_data.append(loaded)
                except (httpx.HTTPError, httpx.TimeoutException) as e:
                    console.print(f"[yellow]⚠[/yellow] Skip image {img_src}: {e}")
                except (FileNotFoundError, ValueError) as e:
                    console.print(f"[yellow]⚠[/yellow] Skip image {img_src}: {e}")
            if image_data:
                console.print(f"[green]✓[/green] Loaded {len(image_data)} images")
            elif image_sources_deduped:
                console.print(f"[yellow]⚠[/yellow] No images could be loaded (all failed)")

        image_paths_list = image_paths_for_embed(image_data) if image_data else []

        # Minimum sources check - ensure we have something to generate from
        if not release_info and not pr_data and not issue_data:
            console.print("[red]Error: No content sources available.[/red]")
            console.print("  All requested PRs/issues failed to fetch.")
            console.print("  Check that the PR/issue numbers exist and are accessible.")
            raise typer.Exit(1)

        # Generate blog
        console.print("[cyan]Generating blog content...[/cyan]")
        if has_release:
            draft = generator.generate_draft(
                release=release_info,
                commits=commits,
                prs=pr_data,
                issues=issue_data,
                docs=doc_data,
                images=image_data,
                image_paths=image_paths_list,
                language=language,
            )
        else:
            # PR/issue only mode
            draft = generator.generate_from_prs(
                prs=pr_data,
                issues=issue_data,
                docs=doc_data,
                images=image_data,
                image_paths=image_paths_list,
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
        if has_release:
            output_dir = get_blogs_dir_path() / release_info.tag_name
        else:
            # Use PR numbers for directory name
            pr_suffix = "-".join([f"pr{p.number}" for p in pr_data]) or "draft"
            output_dir = get_blogs_dir_path() / pr_suffix
        output_dir.mkdir(parents=True, exist_ok=True)

        MarkdownFormatter.save(draft, release_info, output_dir / "blog.md")
        console.print(f"[green]✓[/green] Saved: {output_dir}/blog.md")

        JsonFormatter.save(
            draft,
            release_info,
            [c.sha for c in commits],
            [p.number for p in pr_data],
            output_dir / "blog.json",
        )
        console.print(f"[green]✓[/green] Saved: {output_dir}/blog.json")

        # Save embedded images so blog markdown image links work
        if image_data and image_paths_list:
            for (path, _), img in zip(image_paths_list, image_data):
                out_path = output_dir / path
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(base64.standard_b64decode(img.data_base64))
            console.print(f"[green]✓[/green] Saved {len(image_data)} images to {output_dir}/images/")

        # Print summary of what was fetched
        summary.print_summary(output_dir)

        if has_release:
            console.print(f"  Edit the draft, then run:")
            console.print(f"  [cyan]blog-generator publish --release {release_info.tag_name}[/cyan]")


@app.command()
def publish(
    release: str = typer.Option(..., help="Release version"),
    platform: str = typer.Option(None, help="Platform (zhihu/xiaohongshu)"),
) -> None:
    """Generate platform-specific versions from approved draft."""
    output_dir = get_blogs_dir_path() / release

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

        # Generate post.json for automated XHS posting
        XiaohongshuFormatter.save_post_json(content, title, tags, output_dir / "xiaohongshu")
        console.print(f"[green]✓[/green] Generated: {output_dir}/xiaohongshu/post.json")

    console.print(f"\n[bold green]✓ Published successfully![/bold green]")
    console.print(f"  Zhihu: {output_dir}/zhihu/content.md")
    console.print(f"  Xiaohongshu: {output_dir}/xiaohongshu/content.md")
    console.print(f"\nTo generate XHS images, run:")
    console.print(f"  [cyan]blog-generator xhs-images --release {release}[/cyan]")


@app.command()
def xhs_images(
    release: str = typer.Option(None, "--release", "-r", help="Blog release or dir name (e.g. v0.16.0 or pr962)"),
    blog_dir: str = typer.Option(None, "--blog-dir", help="Path to blog output dir (alternative to --release)"),
    style: str = typer.Option("tech", "--style", "-s", help="Style for baoyu-xhs-images (e.g. tech)"),
    no_invoke: bool = typer.Option(False, "--no-invoke", help="Only print the command, do not run baoyu"),
) -> None:
    """Generate Xiaohongshu front-page images via baoyu skills (prompts must exist from publish)."""
    if blog_dir:
        output_dir = Path(blog_dir)
    elif release:
        output_dir = get_blogs_dir_path() / release
    else:
        console.print("[red]Error: Specify --release or --blog-dir[/red]")
        raise typer.Exit(1)

    prompts_path = output_dir / "xiaohongshu" / "images" / "prompts.md"
    if not prompts_path.exists():
        console.print(f"[red]Error: Prompts file not found: {prompts_path}[/red]")
        console.print("Run [cyan]blog-generator publish --release <release>[/cyan] first (with platform xiaohongshu or all).")
        raise typer.Exit(1)

    cmd = ["baoyu-xhs-images", str(prompts_path), "--style", style]
    console.print(f"[cyan]Running: {' '.join(cmd)}[/cyan]")
    if no_invoke:
        console.print(f"  (use without --no-invoke to run)")
        return
    try:
        subprocess.run(cmd, check=True)
        console.print(f"[green]✓[/green] XHS images generated under {output_dir}/xiaohongshu/images/")
    except FileNotFoundError:
        console.print("[yellow]baoyu-xhs-images not found in PATH.[/yellow]")
        console.print("Install baoyu-skills, then run manually:")
        console.print(f"  [cyan]baoyu-xhs-images {prompts_path} --style {style}[/cyan]")
        raise typer.Exit(1)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Command failed with exit code {e.returncode}[/red]")
        raise typer.Exit(e.returncode or 1)


@app.command("list")
def list_blogs() -> None:
    """List all generated blogs."""
    if not get_blogs_dir_path().exists():
        console.print("[yellow]No blogs generated yet[/yellow]")
        return

    console.print("[bold]Generated Blogs:[/bold]\n")
    for version_dir in sorted(get_blogs_dir_path().iterdir()):
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
    output_dir = get_blogs_dir_path() / release

    if output_dir.exists():
        shutil.rmtree(output_dir)
        console.print(f"[yellow]Removed existing draft for {release}[/yellow]")

    console.print(f"[cyan]Regenerating {release}...[/cyan]")
    console.print(f"Run: [cyan]blog-generator generate --release {release}[/cyan]")


@app.command("xhs-post")
def xhs_post(
    release: str = typer.Option(..., "--release", "-r", help="Blog release or dir name (e.g. v0.16.0 or pr962)"),
    auto_publish: bool = typer.Option(False, "--auto-publish", help="Auto-click publish button"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Open browser but don't save/publish"),
    generate_images: bool = typer.Option(True, "--images/--no-images", help="Generate images via baoyu-xhs-images"),
) -> None:
    """Post blog to Xiaohongshu (requires Chrome with remote debugging).

    Prerequisites:
    1. Start Chrome with remote debugging:
       open -a 'Google Chrome' --args --remote-debugging-port=9222

    2. Login to Xiaohongshu creator account in that Chrome

    3. Run this command
    """
    output_dir = get_blogs_dir_path() / release

    if not (output_dir / "xiaohongshu" / "content.md").exists():
        console.print(f"[red]Error: XHS content not found for {release}[/red]")
        console.print("Run [cyan]blog-generator publish --release {release}[/cyan] first.")
        raise typer.Exit(1)

    # Generate images if requested
    if generate_images:
        console.print("[cyan]Generating images via baoyu-xhs-images...[/cyan]")
        prompts_path = output_dir / "xiaohongshu" / "images" / "prompts.md"
        if prompts_path.exists():
            try:
                subprocess.run(
                    ["baoyu-xhs-images", str(prompts_path), "--style", "notion"],
                    check=False,  # Don't fail if image generation fails
                )
            except FileNotFoundError:
                console.print("[yellow]⚠ baoyu-xhs-images not found, continuing without images[/yellow]")
        else:
            console.print("[yellow]⚠ Prompts file not found, continuing without images[/yellow]")

    # Load content
    publisher = XhsPublisher()
    try:
        data = publisher.load_content(output_dir)
    except Exception as e:
        console.print(f"[red]Error loading content: {e}[/red]")
        raise typer.Exit(1)

    # Post to XHS
    try:
        publisher.post(data, auto_publish=auto_publish, dry_run=dry_run)
        console.print("\n[green]✓ Done![/green]")
    except ChromeNotRunningError:
        # Error message already printed by publisher
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled by user[/yellow]")
        raise typer.Exit(0)


if __name__ == "__main__":
    app()
