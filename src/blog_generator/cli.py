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
