# GLM-Image Cover Generation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate BigModel's GLM-Image API to generate cover images for Xiaohongshu posts during `blog-generator publish`.

**Architecture:** Add ImageConfig to existing config system, create ImageGenerator module for BigModel API calls, integrate into publish command with --cover flag.

**Tech Stack:** Python 3.11+, httpx, pydantic, existing retry utils

---

### Task 1: Add ImageConfig to Config Model

**Files:**
- Modify: `src/blog_generator/config.py:18-29`
- Test: `tests/test_config.py`

**Step 1: Write the failing test**

```python
# tests/test_config.py

import pytest
from pathlib import Path
import tempfile
import json

from blog_generator.config import Config, ImageConfig


def test_image_config_defaults():
    """ImageConfig should have sensible defaults."""
    config = ImageConfig()
    assert config.base_url == "https://open.bigmodel.cn/api/paas/v4"
    assert config.model == "GLM-Image"
    assert config.size == "1024x1024"


def test_config_with_image_section():
    """Config should accept optional image section with defaults."""
    config_data = {
        "api": {
            "anthropic_auth_token": "test-token",
            "anthropic_base_url": "https://test.com/api"
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write(json.dumps(config_data).encode())
        f.flush()
        config = Config.load(Path(f.name))

        # Should have default image config
        assert config.image.model == "GLM-Image"
        assert config.image.base_url == "https://open.bigmodel.cn/api/paas/v4"

        Path(f.name).unlink()


def test_config_with_custom_image_settings():
    """Config should accept custom image settings."""
    config_data = {
        "api": {
            "anthropic_auth_token": "test-token"
        },
        "image": {
            "base_url": "https://custom.com/api",
            "model": "custom-model",
            "size": "512x512"
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write(json.dumps(config_data).encode())
        f.flush()
        config = Config.load(Path(f.name))

        assert config.image.base_url == "https://custom.com/api"
        assert config.image.model == "custom-model"
        assert config.image.size == "512x512"

        Path(f.name).unlink()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with "ImportError" or "AttributeError"

**Step 3: Write minimal implementation**

```python
# src/blog_generator/config.py

# Add after RetryConfigModel class, before ApiConfig class

class ImageConfig(BaseModel):
    """Image generation API configuration."""
    base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    model: str = "GLM-Image"
    size: str = "1024x1024"


# Modify Config class to include image field:

class Config(BaseModel):
    api: ApiConfig
    image: ImageConfig = Field(default_factory=ImageConfig)
    github_token: Optional[str] = None
    default_language: str = "zh"
    retry: RetryConfigModel = Field(default_factory=RetryConfigModel)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/blog_generator/config.py tests/test_config.py
git commit -m "feat(config): add ImageConfig for GLM-Image integration"
```

---

### Task 2: Create ImageGenerator Module
**Files:**
- Create: `src/blog_generator/generator/image.py`
- Create: `tests/generator/__init__.py`
- Create: `tests/generator/test_image.py`

**Step 1: Write the failing test**

```python
# tests/generator/__init__.py
# (empty file)
```

```python
# tests/generator/test_image.py

import pytest
from unittest.mock import AsyncMock, patch
import base64

from blog_generator.generator.image import ImageGenerator, GeneratedImage, ImageConfig


def test_generated_image_dataclass():
    """GeneratedImage should store image data."""
    img = GeneratedImage(
        image_data=b"fake_image_bytes",
        format="png",
        prompt="test prompt"
    )
    assert img.image_data == b"fake_image_bytes"
    assert img.format == "png"
    assert img.prompt == "test prompt"


def test_image_generator_init():
    """ImageGenerator should initialize with config and auth token."""
    config = ImageConfig(model="GLM-Image")
    generator = ImageGenerator(config, "test-token")
    assert generator.config.model == "GLM-Image"
    assert generator.auth_token == "test-token"


@pytest.mark.asyncio
async def test_generate_image_success():
    """ImageGenerator.generate should return GeneratedImage on success."""
    config = ImageConfig()
    generator = ImageGenerator(config, "test-token")

    # Mock base64 image response
    fake_image_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    fake_base64 = base64.b64encode(fake_image_bytes).decode()

    with patch("httpx.AsyncClient") as mock_client:
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "data": [fake_base64]
        }
        mock_response.raise_for_status = lambda: None

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        result = await generator.generate("test prompt")

        assert isinstance(result, GeneratedImage)
        assert result.image_data == fake_image_bytes
        assert result.format == "png"
        assert result.prompt == "test prompt"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/generator/test_image.py -v`
Expected: FAIL with "ModuleNotFoundError" or "ImportError"

**Step 3: Write minimal implementation**

```python
# src/blog_generator/generator/image.py

"""Image generation using BigModel GLM-Image API."""

import base64
from dataclasses import dataclass
from typing import Optional

import httpx

from blog_generator.config import ImageConfig


@dataclass
class GeneratedImage:
    """Result from image generation."""
    image_data: bytes
    format: str
    prompt: str


class ImageGenerator:
    """Generate images using BigModel GLM-Image API."""

    def __init__(self, config: ImageConfig, auth_token: str):
        self.config = config
        self.auth_token = auth_token

    async def generate(
        self,
        prompt: str,
        size: Optional[str] = None,
    ) -> GeneratedImage:
        """Generate image from prompt using GLM-Image API.

        Args:
            prompt: Text prompt for image generation
            size: Image size (e.g., "1024x1024"), defaults to config setting

        Returns:
            GeneratedImage with raw image bytes

        Raises:
            httpx.HTTPError: On API failure
        """
        image_size = size or self.config.size

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.config.base_url}/images/generations",
                headers={
                    "Authorization": f"Bearer {self.auth_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.config.model,
                    "prompt": prompt,
                    "size": image_size,
                    "response_format": "b64_json",
                },
            )
            response.raise_for_status()

            data = response.json()

            # Extract base64 image from response
            image_base64 = data["data"][0]
            image_data = base64.b64decode(image_base64)

            # Detect format from image bytes
            if image_data.startswith(b"\x89PNG"):
                img_format = "png"
            elif image_data.startswith(b"\xff\xd8\xff"):
                img_format = "jpeg"
            else:
                img_format = "png"  # Default fallback

            return GeneratedImage(
                image_data=image_data,
                format=img_format,
                prompt=prompt,
            )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/generator/test_image.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/blog_generator/generator/image.py tests/generator/__init__.py tests/generator/test_image.py
git commit -m "feat: add ImageGenerator module for BigModel GLM-Image API"
```

---

### Task 3: Add Cover Prompt Builder Helper
**Files:**
- Modify: `src/blog_generator/formatter/xiaohongshu.py:154-163`
- Modify: `tests/test_xiaohongshu_formatter.py`

**Step 1: Write the failing test**

```python
# tests/test_xiaohongshu_formatter.py (append to existing file)

from blog_generator.formatter.xiaohongshu import XiaohongshuFormatter


def test_build_cover_prompt():
    """Should build a cover image prompt from title and content."""
    title = "vLLM-Omni v0.16.0 Release"
    content = "This release introduces multimodal inference support with new features for image and audio processing."

    prompt = XiaohongshuFormatter.build_cover_prompt(title, content)

    assert "vLLM-Omni v0.16.0 Release" in prompt
    assert "Clean, minimalist" in prompt or "tech aesthetic" in prompt
    assert len(prompt) > 50  # Should be a meaningful prompt


def test_build_cover_prompt_truncates_long_title():
    """Should truncate very long titles in cover prompt."""
    title = "This is an extremely long title that goes on and on and should be truncated to fit"
    content = "Short content"

    prompt = XiaohongshuFormatter.build_cover_prompt(title, content)

    # Title should be truncated
    assert len(title[:30]) == 30
    assert title[:30] in prompt
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_xiaohongshu_formatter.py::test_build_cover_prompt -v`
Expected: FAIL with "AttributeError"

**Step 3: Write minimal implementation**

```python
# src/blog_generator/formatter/xiaohongshu.py

# Add this static method after the update_post_json_images method:

    @staticmethod
    def build_cover_prompt(title: str, content: str) -> str:
        """Build a cover image prompt from blog title and content.

        Args:
            title: Blog title
            content: Blog content (markdown)

        Returns:
            Image generation prompt
        """
        # Extract first 200 chars of content for context
        summary = content[:200].replace('\n', ' ')

        return f"""Technical blog cover image for: {title[:30]}

Style: Clean, minimalist, tech aesthetic
Colors: Blue gradient with white accents
Elements: Abstract AI/cloud/network visualization
Text overlay: {title[:30]}
Context: {summary}"""
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_xiaohongshu_formatter.py::test_build_cover_prompt -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/blog_generator/formatter/xiaohongshu.py tests/test_xiaohongshu_formatter.py
git commit -m "feat: add build_cover_prompt helper to XiaohongshuFormatter"
```

---

### Task 4: Integrate Image Generation into Publish Command
**Files:**
- Modify: `src/blog_generator/cli.py:386-431`
- Modify: `tests/test_cli.py` (or create integration test)

**Step 1: Write the failing test**

```python
# tests/test_cli.py (or new file tests/test_publish_integration.py)

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path
import tempfile
import json

from blog_generator.cli import publish
from typer.testing import CliRunner

runner = CliRunner()


def test_publish_with_cover_generation():
    """Publish command should generate cover image for Xiaohongshu."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Setup blog directory
        blog_dir = Path(tmpdir) / "v0.16.0"
        blog_dir.mkdir()
        xhs_dir = blog_dir / "xiaohongshu"
        xhs_dir.mkdir(parents=True)

        # Create blog.json
        blog_json = {
            "title": "Test Release",
            "content_md": "Test content",
            "tags": ["ai", "llm"]
        }
        (blog_dir / "blog.json").write_text(json.dumps(blog_json))

        # Create blog.md
        (blog_dir / "blog.md").write_text("# Test Release\n\nTest content")

        # Create xiaohongshu content
        (xhs_dir / "content.md").write_text("Test content")

        # Mock ImageGenerator
        with patch("blog_generator.cli.ImageGenerator") as mock_gen_class:
            mock_generator = MagicMock()
            mock_generator.generate = AsyncMock(return_value=MagicMock(
                image_data=b"\x89PNG\r\nfake",
                format="png"
            ))
            mock_gen_class.return_value = mock_generator

            # Run publish command
            result = runner.invoke(publish, ["--release", "v0.16.0", "--platform", "xiaohongshu"])

            # Check cover image was generated
            cover_path = xhs_dir / "cover.png"
            assert cover_path.exists()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py::test_publish_with_cover_generation -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/blog_generator/cli.py

# Add import at top (~line 30):
from blog_generator.generator.image import ImageGenerator

# Modify the publish command (around line 386):
@app.command()
def publish(
    release: str = typer.Option(..., help="Release version"),
    platform: str = typer.Option(None, help="Platform (zhihu/xiaohongshu)"),
    generate_cover: bool = typer.Option(True, "--cover/--no-cover", help="Generate cover image via GLM-Image"),
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

        # Generate cover image with GLM-Image
        if generate_cover:
            config = get_config()
            generator = ImageGenerator(config.image, config.api.anthropic_auth_token)

            console.print("[cyan]Generating cover image with GLM-Image...[/cyan]")

            try:
                cover_prompt = XiaohongshuFormatter.build_cover_prompt(title, content)
                cover_image = asyncio.run(generator.generate(cover_prompt))

                # Save cover image
                images_dir = output_dir / "xiaohongshu" / "images"
                images_dir.mkdir(parents=True, exist_ok=True)
                cover_path = images_dir / "cover.png"
                cover_path.write_bytes(cover_image.image_data)

                console.print(f"[green]✓[/green] Generated cover: {cover_path}")

                # Update post.json with cover image path
                post_json_path = output_dir / "xiaohongshu" / "post.json"
                if post_json_path.exists():
                    with open(post_json_path) as f:
                        post_data = json.load(f)
                    # Prepend cover image to images list
                    if str(cover_path.resolve()) not in post_data.get("images", []):
                        post_data["images"] = [str(cover_path.resolve())] + post_data.get("images", [])
                        with open(post_json_path, "w") as f:
                            json.dump(post_data, f, ensure_ascii=False, indent=2)

            except Exception as e:
                console.print(f"[yellow]⚠[/yellow] Failed to generate cover image: {e}")
                console.print("  Continuing without cover image")

    console.print(f"\n[bold green]✓ Published successfully![/bold green]")
    console.print(f"  Zhihu: {output_dir}/zhihu/content.md")
    console.print(f"  Xiaohongshu: {output_dir}/xiaohongshu/content.md")
    if platform is None or platform == "xiaohongshu":
        console.print(f"\nXHS images available at: {output_dir}/xiaohongshu/images/")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py::test_publish_with_cover_generation -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/blog_generator/cli.py tests/test_cli.py
git commit -m "feat: integrate GLM-Image cover generation into publish command"
```

---

### Task 5: Update README Documentation
**Files:**
- Modify: `README.md:108-124`

**Step 1: Update documentation**

Add documentation for the new cover image feature:

```markdown
# In README.md, update the Xiaohongshu Image Generation section (around line 109):

## Xiaohongshu Image Generation

Cover images are now automatically generated during `blog-generator publish` using GLM-Image:

```bash
# Publish with cover image (default)
blog-generator publish --release v0.16.0

# Publish without cover image
blog-generator publish --release v0.16.0 --no-cover
```

The cover image is saved to `blogs/v0.16.0/xiaohongshu/images/cover.png` and automatically added to `post.json`.

**Configuration:** Add the `image` section to `blogs/config.json`:

```json
{
  "image": {
    "base_url": "https://open.bigmodel.cn/api/paas/v4",
    "model": "GLM-Image",
    "size": "1024x1024"
  }
}
```

For additional carousel images, use baoyu-skills:
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update README with GLM-Image cover generation"
```

---

### Task 6: Final Verification
**Files:** None (verification only)

**Step 1: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS

**Step 2: Test the command manually**

```bash
# Test with a real blog
blog-generator publish --release <existing_release>
```

Expected: Cover image generated at `xiaohongshu/images/cover.png`

**Step 3: Final commit (if any fixes needed)**

```bash
git status
# If clean, no additional commit needed
```

---

## Summary

| Task | Description | Files Changed |
|------|-------------|---------------|
| 1 | Add ImageConfig to config | config.py, test_config.py |
| 2 | Create ImageGenerator module | generator/image.py, tests/generator/ |
| 3 | Add cover prompt builder | formatter/xiaohongshu.py |
| 4 | Integrate into publish command | cli.py |
| 5 | Update README documentation | README.md |
| 6 | Final verification | tests/ |
