# vLLM-Omni Blog Generator

Generate technical blog posts for vLLM-Omni releases, targeting Zhihu and Xiaohongshu.

## Quick Start

```bash
# Build
docker build -t blog-generator .

# Generate blog for latest release
docker run --rm -v ./blogs:/app/blogs blog-generator generate --latest

# Generate blog for specific release with context
docker run --rm -v ./blogs:/app/blogs blog-generator generate \
  --release v0.16.0 \
  --issue 1666 \
  --pr 1197 \
  --doc docs/design/architecture_overview.md

# Edit the generated draft
vim blogs/v0.16.0/blog.md

# Publish to platform formats
docker run --rm -v ./blogs:/app/blogs blog-generator publish --release v0.16.0
```

## Configuration

Create `blogs/config.json`:

```json
{
  "api": {
    "anthropic_auth_token": "your-token",
    "anthropic_base_url": "https://open.bigmodel.cn/api/anthropic",
    "default_model": "glm-5",
    "timeout_ms": 3000000
  },
  "github_token": "ghp_xxx",
  "default_language": "zh"
}
```

## Output Structure

```
blogs/
├── config.json
├── v0.16.0/
│   ├── blog.md              # Editable draft
│   ├── blog.json            # Structured metadata
│   ├── zhihu/
│   │   └── content.md
│   └── xiaohongshu/
│       ├── content.md
│       └── images/
│           └── prompts.md
```

## Commands

### generate

Generate a blog draft for a release.

```bash
# Latest release
docker run --rm -v ./blogs:/app/blogs blog-generator generate --latest

# Specific release
docker run --rm -v ./blogs:/app/blogs blog-generator generate --release v0.16.0

# With additional context
docker run --rm -v ./blogs:/app/blogs blog-generator generate \
  --release v0.16.0 \
  --issue 1666 \
  --pr 1197 \
  --doc docs/design/architecture_overview.md

# Dry run (preview without saving)
docker run --rm -v ./blogs:/app/blogs blog-generator generate --latest --dry-run
```

### publish

Generate platform-specific versions from an edited draft.

```bash
docker run --rm -v ./blogs:/app/blogs blog-generator publish --release v0.16.0
```

### list

List all generated blogs.

```bash
docker run --rm -v ./blogs:/app/blogs blog-generator list
```

### regenerate

Regenerate a draft (overwrites existing).

```bash
docker run --rm -v ./blogs:/app/blogs blog-generator regenerate --release v0.16.0
```

## Xiaohongshu Image Generation

After publishing, generate cover images using baoyu-skills:

```bash
/baoyu-xhs-images blogs/v0.16.0/xiaohongshu/images/prompts.md --style tech
```

**Test example (PR blog):** For a PR-only blog (e.g. PR 962), generate then publish with the blog dir name (e.g. `pr962`), then run baoyu on the generated prompts:

```bash
blog-generator generate --pr 962
blog-generator publish --release pr962
/baoyu-xhs-images blogs/pr962/xiaohongshu/images/prompts.md --style tech
```

## Development

```bash
# Build Docker image
docker build -t blog-generator .

# Run locally (requires Python 3.11+)
pip install -e .
blog-generator generate --latest
```
