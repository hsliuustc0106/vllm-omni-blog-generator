"""Xiaohongshu platform formatter."""

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


@dataclass
class XhsPostData:
    """Data structure for Xiaohongshu post.json."""
    title: str
    content: str
    images: list[str]
    tags: list[str]
    ready_to_post: bool = True


class XiaohongshuFormatter:
    @staticmethod
    def format(
        content_md: str,
        title: str,
        tags: list[str],
        pr_numbers: list[int] = None,
        issue_numbers: list[int] = None,
    ) -> tuple[str, str]:
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

        # Build references for ending prompt
        refs = []
        if pr_numbers:
            refs.extend([f"PR #{n}" for n in pr_numbers])
        if issue_numbers:
            refs.extend([f"Issue #{n}" for n in issue_numbers])
        refs_text = " | ".join(refs) if refs else ""

        # Generate image prompts (cover and ending only - content uses PR images)
        image_prompts = f"""# Xiaohongshu Image Prompts

## Cover Image Prompt
Generate a cover image for a technical blog post about vLLM-Omni.

Title: {title}

Style Guidelines:
- Clean, minimalist, tech aesthetic
- Modern and professional design
- Suitable for social media sharing (Xiaohongshu)

Color Scheme:
- Blue gradient background
- White accents for contrast

Visual Elements:
- Abstract AI visualization
- Cloud computing imagery
- Network/connection patterns

Text Overlay:
- Main title text (prominent, readable)

## Ending Image Prompt
Generate an ending/call-to-action image for a technical blog post.

Main Text: "关注获取更多 AI 技术分享"

Project: github.com/vllm-project/vllm-omni

References: {refs_text if refs_text else 'See blog post for details'}

Style Guidelines:
- Clean, minimalist, tech aesthetic
- Match the cover image style

Color Scheme:
- Blue gradient background (matching cover)
- White text for contrast

Visual Elements:
- "Follow for more" iconography
- Social media engagement symbols
- QR code or link placeholder (optional)
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

    @staticmethod
    def strip_markdown(text: str) -> str:
        """Convert markdown to plain text for XHS.

        - Remove **bold** markers
        - Keep links as text
        - Remove image syntax entirely (don't keep alt text - images are separate)
        """
        # Remove image syntax entirely: ![alt](url) -> (empty)
        text = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', text)

        # Remove **bold** and *italic* markers
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)

        # Remove ## headers but keep text
        text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)

        # Remove [link](url) but keep link text
        text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)

        # Clean up extra whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()

    @staticmethod
    def _truncate_title(title: str, max_length: int = 20) -> str:
        """Smart title truncation for XHS.

        Tries to cut off whole words instead of mid-sentence.
        """
        if len(title) <= max_length:
            return title

        # Split into words and trim until we fits
        words = title.split()
        result = []
        current_length = 0

        for word in words:
            word_len = len(word)
            if current_length == 0:
                # First word
                if word_len <= max_length:
                    result.append(word)
                    current_length = word_len
                else:
                    # Word itself is too long, truncate it
                    return word[:max_length]
            elif current_length + 1 + word_len <= max_length:
                # Can add this word with space
                result.append(word)
                current_length += 1 + word_len
            else:
                # Can't fit more words, stop
                break

        return ' '.join(result) if result else title[:max_length]

    @staticmethod
    def build_cover_prompt(title: str, content: str) -> str:
        """Build an image generation prompt for cover image.

        Args:
            title: Blog post title (truncated to 30 chars for text overlay)
            content: Blog content (first 200 chars used for context)

        Returns:
            Formatted prompt string for image generation
        """
        # Truncate title to 30 chars for text overlay
        truncated_title = title[:30] if len(title) > 30 else title

        # Extract first 200 chars of content for context
        content_context = content[:200] if len(content) > 200 else content

        prompt = f"""Generate a cover image for a technical blog post.

Title: {truncated_title}

Context: {content_context}

Style Guidelines:
- Clean, minimalist, tech aesthetic
- Modern and professional design
- Suitable for social media sharing

Color Scheme:
- Blue gradient background
- White accents for contrast
- Subtle tech-inspired patterns

Visual Elements:
- Abstract AI visualization
- Cloud computing imagery
- Network/connection patterns
- Modern geometric shapes

Text Overlay:
- Title text: "{truncated_title}"
- Clean sans-serif font
- Positioned for maximum readability

Image Specifications:
- Aspect ratio suitable for Xiaohongshu cover
- High contrast for text visibility
- Professional tech industry style"""

        return prompt

    @staticmethod
    def build_ending_prompt(title: str, pr_numbers: list[int] = None, issue_numbers: list[int] = None) -> str:
        """Build an image generation prompt for ending/CTA image.

        Args:
            title: Blog post title (for style consistency)
            pr_numbers: List of PR numbers to reference
            issue_numbers: List of issue numbers to reference

        Returns:
            Formatted prompt string for image generation
        """
        # Build references text
        refs = []
        if pr_numbers:
            refs.append("PR #" + ", #".join(str(p) for p in pr_numbers))
        if issue_numbers:
            refs.append("Issue #" + ", #".join(str(i) for i in issue_numbers))
        refs_text = " | ".join(refs) if refs else ""

        prompt = f"""A clean, minimalist ending slide for a technical social media post.

Main Text: "关注获取更多 AI 技术分享"

Style: Modern tech aesthetic with blue gradient background, white text.
Layout: Centered text, clean sans-serif font.
{f'References: {refs_text}' if refs_text else ''}

Make it visually appealing and professional."""

        return prompt

    @staticmethod
    def extract_image_paths(content_md: str) -> list[str]:
        """Extract image paths from markdown content.

        Returns list of relative paths like ['images/foo.png', ...]
        """
        pattern = r'!\[[^\]]*\]\(([^)]+)\)'
        matches = re.findall(pattern, content_md)
        return list(dict.fromkeys(matches))  # Remove duplicates, preserve order

    @staticmethod
    def generate_post_json(
        content_md: str,
        title: str,
        tags: list[str],
        output_dir: Path,
        max_title_length: int = 20,
    ) -> XhsPostData:
        """Generate XhsPostData for post.json.

        Args:
            content_md: Full markdown content
            title: Blog title
            tags: List of tags
            output_dir: Output directory (for generating absolute paths)
            max_title_length: Maximum title length (XHS limit)

        Returns:
            XhsPostData ready for JSON serialization
        """
        # Strip markdown to plain text
        plain_content = XiaohongshuFormatter.strip_markdown(content_md)

        # Add engagement prompt
        if "评论区聊聊" not in plain_content:
            plain_content += "\n\n💬 你最期待哪个功能？评论区聊聊！"

        # Extract image paths and convert to absolute
        relative_paths = XiaohongshuFormatter.extract_image_paths(content_md)
        absolute_paths = [
            str((output_dir / rel_path).resolve())
            for rel_path in relative_paths
        ]

        # Truncate title smartly for XHS (20 char limit)
        # Try to cut off words instead of mid-sentence
        truncated_title = XiaohongshuFormatter._truncate_title(title, max_title_length)

        # Clean tags - remove # prefix if present, limit to 5
        clean_tags = []
        for tag in tags[:5]:
            clean_tag = tag.lstrip('#').strip()
            if clean_tag:
                clean_tags.append(clean_tag)

        return XhsPostData(
            title=truncated_title,
            content=plain_content,
            images=absolute_paths,
            tags=clean_tags,
            ready_to_post=True,
        )

    @staticmethod
    def save_post_json(
        content_md: str,
        title: str,
        tags: list[str],
        output_dir: Path,
    ) -> None:
        """Generate and save post.json for Xiaohongshu.

        Args:
            content_md: Full markdown content
            title: Blog title
            tags: List of tags
            output_dir: Xiaohongshu output directory
        """
        # The output_dir is typically blogs/pr962/xiaohongshu
        # We need the blog root for absolute paths
        blog_root = output_dir.parent

        post_data = XiaohongshuFormatter.generate_post_json(
            content_md=content_md,
            title=title,
            tags=tags,
            output_dir=blog_root,
        )

        post_json_path = output_dir / "post.json"
        with open(post_json_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(post_data), f, ensure_ascii=False, indent=2)

    @staticmethod
    def parse_prompts_file(prompts_path: Path) -> list[dict]:
        """Parse prompts.md and extract image prompts.

        Returns list of dicts with:
            - type: 'cover' or 'carousel'
            - title: prompt title
            - prompt: the image prompt text
        """
        content = prompts_path.read_text()

        prompts = []
        current_type = None
        current_title = ""
        current_prompt = []

        lines = content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Detect cover image section
            if '## Cover Image' in line or line.startswith('## Cover'):
                current_type = 'cover'
                i += 1
                continue

            # Detect carousel section
            if '## Carousel' in line or '### Slide' in line:
                # Save previous prompt if exists
                if current_type and current_prompt:
                    prompts.append({
                        'type': current_type,
                        'title': current_title,
                        'prompt': '\n'.join(current_prompt).strip()
                    })
                    current_prompt = []

                if '## Carousel' in line:
                    current_type = 'carousel'
                    i += 1
                    continue
                elif '### Slide' in line:
                    current_type = 'carousel'
                    # Extract slide title (e.g., "### Slide 1: Title")
                    current_title = line.split(':', 1)[-1].strip() if ':' in line else ''
                    i += 1
                    continue

            # Collect prompt content
            if current_type and line:
                current_prompt.append(line)

            i += 1

        # Don't forget the last prompt
        if current_type and current_prompt:
            prompts.append({
                'type': current_type,
                'title': current_title,
                'prompt': '\n'.join(current_prompt).strip()
            })

        return prompts

    @staticmethod
    def select_images_interactive(prompts: list[dict]) -> list[int]:
        """Interactive selection of images to include.

        Uses questionary for user input.

        Args:
            prompts: List of image prompts (from parse_prompts_file)

        Returns:
            List of selected indices (0-indexed)
        """
        from rich.console import Console
        from rich.table import Table

        console = Console()

        # Group prompts by type
        cover_prompts = [(i, p) for i, p in enumerate(prompts) if p['type'] == 'cover']
        carousel_prompts = [(i, p) for i, p in enumerate(prompts) if p['type'] == 'carousel']

        # Show cover image (always included)
        if cover_prompts:
            console.print("\n[bold cyan]Cover Image (always included):[/bold cyan]")
            for idx, p in cover_prompts:
                console.print(f"  • {p['title'][:60]}")

        # Show carousel images with selection
        console.print(f"\n[bold cyan]Carousel Images ({len(carousel_prompts)} available):[/bold cyan]")

        table = Table(show_header=True)
        table.add_column("#", style="cyan")
        table.add_column("Title", style="dim")
        table.add_column("Preview", style="dim", no_wrap=True)

        carousel_idx = 1
        for orig_idx, p in carousel_prompts:
            preview = p['prompt'][:60] + "..." if len(p['prompt']) > 60 else p['prompt']
            table.add_row(str(carousel_idx), p['title'][:40] or f"Slide {carousel_idx}", preview)
            carousel_idx += 1

        console.print(table)

        # Instructions
        console.print("\n  [dim]Enter numbers to select (comma-separated, e.g., 1,2,3)[/dim]")
        console.print("  [dim]Press Enter to select all images[/dim]")

        # Get user selection
        selection = console.input("\n[bold]Select images to include:[/bold] ").strip()

        if not selection:
            # Default: select all
            selected_orig_indices = [orig_idx for orig_idx, _ in carousel_prompts]
        else:
            # Parse selection
            selected_orig_indices = []
            for part in selection.split(','):
                part = part.strip()
                if part.isdigit():
                    carousel_idx = int(part)
                    if 1 <= carousel_idx <= len(carousel_prompts):
                        # Convert 1-indexed carousel position to original index
                        selected_orig_indices.append(carousel_prompts[carousel_idx - 1][0])
                    else:
                        console.print(f"[yellow]Invalid index {carousel_idx}, skipping[/yellow]")

        # Always include cover
        for orig_idx, p in cover_prompts:
            if orig_idx not in selected_orig_indices:
                selected_orig_indices.insert(0, orig_idx)

        console.print(f"\n[green]Selected {len(selected_orig_indices)} images[/green]")
        return selected_orig_indices

    @staticmethod
    def update_post_json_images(
        output_dir: Path,
        selected_image_paths: list[str],
    ) -> None:
        """Update post.json with selected image paths.

        Args:
            output_dir: Xiaohongshu output directory
            selected_image_paths: List of absolute image paths
        """
        post_json_path = output_dir / "post.json"

        if not post_json_path.exists():
            return

        with open(post_json_path, 'r', encoding='utf-8') as f:
            post_data = json.load(f)

        # Update images field
        post_data['images'] = selected_image_paths

        with open(post_json_path, 'w', encoding='utf-8') as f:
            json.dump(post_data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def build_combined_image_paths(
        xhs_images_dir: Path,
        blog_root: Path,
        content_md: str,
    ) -> list[str]:
        """Build combined image path list: [cover] + [PR images] + [end].

        Args:
            xhs_images_dir: Path to xiaohongshu/images directory
            blog_root: Path to blog root (e.g., blogs/pr962)
            content_md: Blog markdown content (to extract PR image paths)

        Returns:
            List of absolute image paths in the correct order
        """
        images = []

        # 1. Cover image (if exists)
        cover_path = xhs_images_dir / "cover.png"
        if cover_path.exists():
            images.append(str(cover_path.resolve()))

        # 2. PR images from blog content
        pr_image_rel_paths = XiaohongshuFormatter.extract_image_paths(content_md)
        for rel_path in pr_image_rel_paths:
            abs_path = (blog_root / rel_path).resolve()
            if abs_path.exists():
                images.append(str(abs_path))

        # 3. Ending image (if exists)
        end_path = xhs_images_dir / "end.png"
        if end_path.exists():
            images.append(str(end_path.resolve()))

        return images
