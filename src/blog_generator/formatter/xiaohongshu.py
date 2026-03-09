"""Xiaohongshu platform formatter."""

from pathlib import Path


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
