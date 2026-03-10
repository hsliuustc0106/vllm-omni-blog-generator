# Xiaohongshu Auto-Publish Design

**Date**: 2026-03-10
**Status**: Approved
**Approach**: CLI command with Chrome CDP automation (Option 1)

## Overview

Add `xhs-post` CLI command to blog-generator for automated posting to Xiaohongshu using Chrome DevTools Protocol (CDP).

## Command Interface

```bash
blog-generator xhs-post --release pr962 [--auto-publish] [--dry-run]
```

| Flag | Description |
|------|-------------|
| `--release <name>` | Blog release directory name (required) |
| `--auto-publish` | Skip review, auto-click 发布 |
| `--dry-run` | Open browser, fill content, but don't save/publish |

**Default behavior**: Fill content + images, save draft, pause for user review.

## Workflow

```
┌─────────────────────────────────────────────────────────────┐
│  blog-generator xhs-post --release pr962                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Load content from xiaohongshu/content.md                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Try baoyu-xhs-images → generate images                  │
│     ├─ Success: Save to xiaohongshu/images/*.png           │
│     └─ Failure: ⚠️ Warning, continue without images         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Connect to Chrome (CDP) at localhost:9222              │
│     ├─ Connected: Continue                                  │
│     └─ Not found: Error + instructions to start Chrome      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  4. Navigate to creator.xiaohongshu.com/publish/publish    │
│     Fill: title, content, tags                              │
│     Upload: images (if available)                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  5. [Default] Save draft → User reviews → User clicks 发布  │
│     [--auto-publish] Click 发布 automatically               │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Structure

**New file**: `src/blog_generator/publisher/xiaohongshu.py`

```
src/blog_generator/
├── cli.py                      # Add xhs-post command
├── publisher/                  # NEW
│   ├── __init__.py
│   └── xiaohongshu.py          # XhsPublisher class
└── ...
```

**XhsPublisher class**:
```python
class XhsPublisher:
    def __init__(self, cdp_port: int = 9222)

    def connect(self) -> bool
        """Connect to Chrome via CDP"""

    def post(self, content: str, images: list[Path],
             tags: list[str], auto_publish: bool = False) -> bool
        """Fill form, upload images, save draft or publish"""

    def generate_images(self, blog_dir: Path) -> list[Path]
        """Call baoyu-xhs-images skill, return image paths"""
```

**Dependencies**:
- CDP WebSocket client (e.g., `websocket-client` or `playwright`)
- Chrome running with `--remote-debugging-port=9222`

**CLI integration** (`cli.py`):
```python
@app.command()
def xhs_post(release: str, auto_publish: bool = False, dry_run: bool = False):
    """Post blog to Xiaohongshu."""
    ...
```

## Error Handling

| Error | Behavior |
|-------|----------|
| Chrome not running | Print: `Please start Chrome with: open -a "Google Chrome" --args --remote-debugging-port=9222` |
| Chrome CDP connection failed | Retry 3x, then exit with error |
| Not logged in to XHS | Exit with "Please login to Xiaohongshu first" |
| Element not found | Save debug screenshot, exit with selector info |
| Rate limited / blocked | Exit with warning, suggest waiting |
| Draft save failed | Retry once, save to local file as backup |
| Image generation failed | ⚠️ Warning, continue without images |

## Recovery

If any step fails, content is already prepared locally. User can:
1. Re-run with same command
2. Manually copy from `blogs/pr962/xiaohongshu/content.md`

## Prerequisites

1. Start Chrome with remote debugging:
   ```bash
   open -a "Google Chrome" --args --remote-debugging-port=9222
   ```

2. Login to Xiaohongshu creator account in that Chrome instance

3. Ensure valid API key for image generation (DashScope/OpenAI/Google)

## Future Enhancements

- Support for scheduling posts
- Multi-account support
- Post analytics tracking
