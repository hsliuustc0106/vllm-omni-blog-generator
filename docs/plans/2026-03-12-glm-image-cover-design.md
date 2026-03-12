# GLM-Image Cover Generation Design

## Overview

Integrate BigModel's GLM-Image API to generate cover images for Xiaohongshu posts during the `blog-generator publish` command.

## Configuration

Add an `image` section to `blogs/config.json`:

```json
{
  "api": {
    "anthropic_auth_token": "...",
    "anthropic_base_url": "https://open.bigmodel.cn/api/anthropic",
    "default_model": "glm-5"
  },
  "image": {
    "base_url": "https://open.bigmodel.cn/api/paas/v4",
    "model": "GLM-Image",
    "size": "1024x1024"
  },
  "github_token": "..."
}
```

### Config Model Changes

Add `ImageConfig` to `src/blog_generator/config.py`:

```python
class ImageConfig(BaseModel):
    base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    model: str = "GLM-Image"
    size: str = "1024x1024"

class Config(BaseModel):
    api: ApiConfig
    image: ImageConfig = Field(default_factory=ImageConfig)
    github_token: Optional[str] = None
    default_language: str = "zh"
```

## Image Generator Module

Create `src/blog_generator/generator/image.py`:

```python
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

    async def generate(self, prompt: str, size: str = None) -> GeneratedImage:
        """Generate image from prompt."""
        # POST {base_url}/images/generations
        # Returns base64-encoded image
```

**API Details:**
- Endpoint: `POST {base_url}/images/generations`
- Headers: `Authorization: Bearer {auth_token}`
- Body: `{"model": "GLM-Image", "prompt": "...", "size": "1024x1024", "response_format": "b64_json"}`
- Response: Base64-encoded image

**Error Handling:**
- Use existing retry utils for exponential backoff
- Graceful degradation: log warning and continue without cover image on failure

## Publish Command Integration

Modify `src/blog_generator/cli.py` to generate cover image during publish:

```python
@app.command()
def publish(
    release: str = typer.Option(...),
    platform: str = typer.Option(None),
    generate_cover: bool = typer.Option(True, "--cover/--no-cover"),
) -> None:
```

**Flow:**
1. Load existing config
2. Generate platform content (zhihu, xiaohongshu)
3. For xiaohongshu: extract cover prompt from title/content
4. Call `ImageGenerator.generate()`
5. Save to `xiaohongshu/cover.png`
6. Update `post.json.images` with cover path

## Cover Prompt Extraction

New helper function in `XiaohongshuFormatter`:

```python
def _extract_cover_prompt(title: str, content: str) -> str:
    """Build a cover image prompt from blog title and summary."""
    summary = content[:200].replace('\n', ' ')
    return f"""Technical blog cover image for: {title}

Style: Clean, minimalist, tech aesthetic
Colors: Blue gradient with white accents
Elements: Abstract AI/cloud/network visualization
Text overlay: {title[:30]}
Context: {summary}"""
```

## Output Structure

```
blogs/
├── v0.16.0/
│   ├── blog.md
│   ├── xiaohongshu/
│   │   ├── content.md
│   │   ├── images/
│   │   │   └── prompts.md
│   │   ├── cover.png          # NEW: generated cover
│   │   └── post.json
```

**post.json update:**
```json
{
  "images": [
    "/path/to/blogs/v0.16.0/xiaohongshu/cover.png",
    ... other carousel images
  ]
}
```

## Dependencies

No new dependencies required:
- Uses existing `httpx.AsyncClient`
- Uses existing `retry` utils

## Testing

```bash
# Normal publish with cover
blog-generator publish --release v0.16.0

# Skip cover generation
blog-generator publish --release v0.16.0 --no-cover
```
