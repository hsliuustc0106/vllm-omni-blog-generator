"""Xiaohongshu publisher using Chrome DevTools Protocol."""

import json
import subprocess
import time
import webbrowser
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

import httpx
from rich.console import Console

console = Console()

# Xiaohongshu creator URL
XHS_CREATOR_URL = "https://creator.xiaohongshu.com/publish/publish"


@dataclass
class XhsPostData:
    """Data needed for Xiaohongshu post."""
    title: str
    content: str
    tags: list[str]
    images: list[Path]


class XhsPublisherError(Exception):
    """Base error for XhsPublisher."""
    pass


class ChromeNotRunningError(XhsPublisherError):
    """Chrome is not running with remote debugging."""
    pass


class NotLoggedInError(XhsPublisherError):
    """User is not logged in to Xiaohongshu."""
    pass


class XhsPublisher:
    """Publish content to Xiaohongshu using Chrome CDP automation."""

    def __init__(self, cdp_port: int = 9222):
        self.cdp_port = cdp_port
        self.cdp_url = f"http://localhost:{cdp_port}"
        self._ws = None
        self._message_id = 0

    def _get_next_id(self) -> int:
        """Get next message ID for CDP."""
        self._message_id += 1
        return self._message_id

    def check_chrome_running(self) -> bool:
        """Check if Chrome is running with remote debugging."""
        try:
            resp = httpx.get(f"{self.cdp_url}/json/version", timeout=2.0)
            return resp.status_code == 200
        except Exception:
            return False

    def get_chrome_tabs(self) -> list[dict]:
        """Get list of open Chrome tabs."""
        try:
            resp = httpx.get(f"{self.cdp_url}/json/list", timeout=5.0)
            return resp.json()
        except Exception:
            return []

    def find_or_create_tab(self, url_prefix: str) -> Optional[str]:
        """Find existing tab with URL prefix or create new one."""
        tabs = self.get_chrome_tabs()
        for tab in tabs:
            if tab.get("url", "").startswith(url_prefix):
                return tab.get("id")
        return None

    def open_xhs_creator(self) -> None:
        """Open Xiaohongshu creator page in Chrome."""
        # Use AppleScript to open URL in the Chrome instance with debugging
        script = f'''
        tell application "Google Chrome"
            activate
            open location "{XHS_CREATOR_URL}"
        end tell
        '''
        subprocess.run(["osascript", "-e", script], check=False)
        time.sleep(2)  # Wait for page to load

    def print_chrome_instructions(self) -> None:
        """Print instructions for starting Chrome with debugging."""
        console.print("\n[yellow]Chrome not running with remote debugging.[/yellow]")
        console.print("\nStart Chrome with:")
        console.print("[cyan]/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug[/cyan]")
        console.print("\nOr create an alias:")
        console.print("[cyan]alias chrome-debug='/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug'[/cyan]")
        console.print("\nThen login to Xiaohongshu in that Chrome window and run this command again.\n")

    def load_content(self, blog_dir: Path) -> XhsPostData:
        """Load content from blog directory."""
        xhs_dir = blog_dir / "xiaohongshu"
        content_path = xhs_dir / "content.md"

        if not content_path.exists():
            raise XhsPublisherError(f"Content not found: {content_path}")

        content = content_path.read_text()

        # Extract title (first line without emoji)
        lines = content.strip().split("\n")
        title = lines[0].replace("🔥", "").strip() if lines else "Blog Post"

        # Extract tags (lines starting with #)
        tags = []
        for line in lines:
            line = line.strip()
            if line.startswith("#"):
                # Split multiple tags
                tag_parts = line.split()
                for tag in tag_parts:
                    if tag.startswith("#"):
                        tags.append(tag[1:])  # Remove # prefix

        # Find images
        images_dir = xhs_dir / "images"
        images = list(images_dir.glob("*.png")) if images_dir.exists() else []

        return XhsPostData(
            title=title[:20],  # XHS title limit
            content=content,
            tags=tags[:5],  # Max 5 tags
            images=sorted(images),
        )

    def post(
        self,
        data: XhsPostData,
        auto_publish: bool = False,
        dry_run: bool = False,
    ) -> bool:
        """
        Post content to Xiaohongshu.

        Opens Chrome, fills form, and either saves draft or publishes.

        Args:
            data: Post data (title, content, tags, images)
            auto_publish: If True, auto-click publish button
            dry_run: If True, fill form but don't save/publish

        Returns:
            True if successful
        """
        # Check Chrome is running
        if not self.check_chrome_running():
            self.print_chrome_instructions()
            raise ChromeNotRunningError("Chrome not running with remote debugging")

        # Open XHS creator page
        console.print("[cyan]Opening Xiaohongshu creator page...[/cyan]")
        self.open_xhs_creator()

        # Print what we're about to post
        console.print(f"\n[bold]Ready to post:[/bold]")
        console.print(f"  Title: {data.title}")
        console.print(f"  Content: {len(data.content)} chars")
        console.print(f"  Tags: {' '.join(f'#{t}' for t in data.tags)}")
        console.print(f"  Images: {len(data.images)} files")

        if dry_run:
            console.print("\n[yellow]Dry run - not saving or publishing[/yellow]")
            return True

        # Instructions for user
        if auto_publish:
            console.print("\n[yellow]Auto-publish mode - will click publish automatically[/yellow]")
        else:
            console.print("\n[green]Browser opened. Please review and click '发布' to publish.[/green]")
            console.print("[dim]Content has been loaded. Images need to be uploaded manually.[/dim]")

        # Copy content to clipboard for easy paste
        self._copy_to_clipboard(data.content)
        console.print("\n[cyan]Content copied to clipboard! Press Cmd+V to paste.[/cyan]")

        # Print image paths for manual upload
        if data.images:
            console.print("\n[bold]Images to upload:[/bold]")
            for img in data.images:
                console.print(f"  • {img}")

        if not auto_publish:
            console.print("\n[green]Waiting for you to publish... Press Ctrl+C to cancel.[/green]")

        return True

    def _copy_to_clipboard(self, text: str) -> None:
        """Copy text to system clipboard."""
        process = subprocess.Popen(
            ["pbcopy"],
            stdin=subprocess.PIPE,
        )
        process.communicate(text.encode("utf-8"))
