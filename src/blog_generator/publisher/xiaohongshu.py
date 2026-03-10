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

        # Copy content to clipboard first
        self._copy_to_clipboard(data.content)
        console.print("[cyan]Content copied to clipboard.[/cyan]")

        # Automate the posting process
        if auto_publish:
            console.print("\n[yellow]Auto-publish mode - filling form and publishing...[/yellow]")
            self.fill_and_publish(data, dry_run=False)
        else:
            console.print("\n[green]Filling form... Please review before it publishes.[/green]")
            self.fill_and_publish(data, dry_run=True)
            console.print("\n[green]Form filled. Please review and click '发布' to publish.[/green]")
            console.print("[dim]Images may need to be uploaded manually via drag & drop.[/dim]")

        return True

    def _copy_to_clipboard(self, text: str) -> None:
        """Copy text to system clipboard."""
        process = subprocess.Popen(
            ["pbcopy"],
            stdin=subprocess.PIPE,
        )
        process.communicate(text.encode("utf-8"))

    def fill_and_publish(
        self,
        data: "XhsPostData",
        dry_run: bool = False,
    ) -> bool:
        """
        Fill the form and publish using keyboard shortcuts.

        This automates:
        1. Activate Chrome
        2. Paste the content (Cmd+V)
        3. Upload images (opens Finder)
        4. Click publish button
        """
        # Content is already in clipboard from post()

        # Wait for page to be ready
        time.sleep(2)

        # Simple approach: activate Chrome and use keyboard shortcuts
        console.print("[cyan]Activating Chrome...[/cyan]")
        activate_script = '''
        tell application "Google Chrome"
            activate
        end tell
        '''
        subprocess.run(["osascript", "-e", activate_script], check=False)
        time.sleep(1)

        # Use cliclick for clicking, then AppleScript for paste
        CLICLICK_PATH = "/opt/homebrew/bin/cliclick"
        try:
            # Click in the editor area
            console.print("[cyan]Clicking editor area...[/cyan]")
            click_result = subprocess.run(
                [CLICLICK_PATH, "c:500,400"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if click_result.returncode != 0:
                console.print(f"[yellow]Click failed: {click_result.stderr}[/yellow]")
                raise FileNotFoundError("cliclick click failed")

            time.sleep(0.5)

            # Use AppleScript for Cmd+V (more reliable than cliclick for key combos)
            console.print("[cyan]Pasting content...[/cyan]")
            paste_script = '''
            tell application "System Events"
                keystroke "v" using command down
            end tell
            '''
            paste_result = subprocess.run(
                ["osascript", "-e", paste_script],
                capture_output=True,
                text=True,
                timeout=10
            )

            if paste_result.returncode == 0:
                console.print("[green]✓ Content pasted![/green]")
            else:
                console.print(f"[yellow]Paste may have failed: {paste_result.stderr}[/yellow]")
                console.print("[yellow]Please press Cmd+V manually to paste.[/yellow]")

        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            # Fallback: just print instructions
            console.print(f"[yellow]Automation not available: {e}[/yellow]")
            console.print("\n[bold]Manual steps:[/bold]")
            console.print("  1. Click in the editor area")
            console.print("  2. Press Cmd+V to paste content")
            console.print("  3. Upload images")
            console.print("  4. Click 发布")

        # Upload images using AppleScript
        if data.images:
            console.print(f"[cyan]Opening images for upload...[/cyan]")
            for img in data.images:
                self._upload_image_via_script(img)
                time.sleep(0.5)

        if dry_run:
            console.print("\n[yellow]Dry run - please click 发布 manually[/yellow]")
            return True

        # Click publish button
        console.print("[cyan]Attempting to click publish...[/cyan]")
        try:
            # Try clicking in bottom-right area where publish button usually is
            subprocess.run(
                [CLICLICK_PATH, "c:1200,800"],
                capture_output=True,
                text=True,
                timeout=5
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            console.print("[yellow]Please click the 发布 button manually.[/yellow]")

        return True

    def _upload_image_via_script(self, image_path: Path) -> None:
        """Upload a single image using AppleScript file chooser."""
        # This is tricky - we need to interact with the file chooser
        # For now, we'll use a simpler approach: open Finder with the image
        abs_path = image_path.resolve()

        # Open Finder showing the image
        subprocess.run(["open", "-R", str(abs_path)], check=False)
        console.print(f"  [dim]Opened Finder for: {abs_path.name}[/dim]")
        console.print("  [yellow]Please drag the image to the XHS upload area[/yellow]")
