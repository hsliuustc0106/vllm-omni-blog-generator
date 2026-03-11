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
