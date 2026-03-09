# vLLM-Omni Blog Generator Design

## Overview

A Docker-based CLI tool that automatically generates technical blog posts for vLLM-Omni releases, targeting Zhihu and Xiaohongshu platforms.

## Requirements Summary

| Aspect | Decision |
|--------|----------|
| **Repo** | Standalone `vllm-omni-blog-generator` |
| **Deployment** | Docker container, on-demand |
| **Trigger** | CLI: `generate --release vX.Y.Z` or `--latest` |
| **Data sources** | GitHub API (commits, releases, PRs, issues, docs via URL) |
| **LLM** | Claude API via Zhipu endpoint (glm-5) |
| **Config** | `blogs/config.json` |
| **Workflow** | 2-phase: `generate` → edit → `publish` |
| **Output formats** | Markdown, JSON, Zhihu, Xiaohongshu (+ images via baoyu-skills) |
| **Audience** | General AI enthusiasts (Chinese, accessible tone) |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Container                          │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                  Blog Generator CLI                      ││
│  │                                                          ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ││
│  │  │ GitHub       │  │   Content    │  │   Output     │  ││
│  │  │ Fetcher      │─▶│   Generator  │─▶│   Formatter  │  ││
│  │  │              │  │  (Claude API)│  │              │  ││
│  │  └──────────────┘  └──────────────┘  └──────────────┘  ││
│  └─────────────────────────────────────────────────────────┘│
│                          │                                   │
│                          ▼                                   │
│                    Mounted Volume                            │
│                 (./blogs:/app/blogs)                         │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
vllm-omni-blog-generator/
├── Dockerfile
├── pyproject.toml
├── README.md
├── src/
│   └── blog_generator/
│       ├── __init__.py
│       ├── cli.py              # CLI entry point (typer)
│       ├── config.py           # Load config.json
│       ├── fetcher/
│       │   ├── __init__.py
│       │   ├── github.py       # Fetch commits, releases, PRs, issues
│       │   └── docs.py         # Fetch docs (local or GitHub URL)
│       ├── generator/
│       │   ├── __init__.py
│       │   └── claude.py       # Claude API client
│       ├── formatter/
│       │   ├── __init__.py
│       │   ├── markdown.py     # Generate blog.md
│       │   ├── json.py         # Generate blog.json
│       │   ├── zhihu.py        # Zhihu format
│       │   └── xiaohongshu.py  # Xiaohongshu format + image prompts
│       └── prompts/
│           ├── __init__.py
│           ├── draft.py        # Prompt for generating draft
│           └── platform.py     # Prompt for platform versions
└── blogs/                      # Created by user, gitignored
    └── config.json
```

## Configuration

**`blogs/config.json`:**
```json
{
  "api": {
    "anthropic_auth_token": "xxx",
    "anthropic_base_url": "https://open.bigmodel.cn/api/anthropic",
    "default_model": "glm-5",
    "timeout_ms": 3000000
  },
  "github_token": "ghp_xxx",
  "default_language": "zh"
}
```

**For Xiaohongshu images (`~/.baoyu-skills/.env`):**
```bash
GOOGLE_API_KEY=your-google-api-key
```

## CLI Commands

### Phase 1: Generate Draft

```bash
docker run --rm -v ./blogs:/app/blogs blog-generator generate --latest
docker run --rm -v ./blogs:/app/blogs blog-generator generate --release v0.16.0
docker run --rm -v ./blogs:/app/blogs blog-generator generate --release v0.16.0 \
  --issue 1666 \
  --pr 1197 --pr 1652 \
  --doc docs/design/architecture_overview.md
```

### Phase 2: Publish

```bash
docker run --rm -v ./blogs:/app/blogs blog-generator publish --release v0.16.0
docker run --rm -v ./blogs:/app/blogs blog-generator publish --release v0.16.0 --platform zhihu
```

### Utility Commands

```bash
blog-generator list                          # List all generated blogs
blog-generator regenerate --release v0.16.0  # Regenerate draft (overwrites)
```

## Output Structure

```
blogs/
├── config.json
├── v0.16.0/
│   ├── blog.md              # Draft - editable by user
│   ├── blog.json            # Structured metadata + content
│   ├── approved             # Empty marker file (created when approved)
│   ├── zhihu/               # Generated after approval
│   │   └── content.md
│   └── xiaohongshu/         # Generated after approval
│       ├── content.md
│       └── images/
│           └── prompts.md   # For baoyu-xhs-images
```

**blog.json structure:**
```json
{
  "version": "v0.16.0",
  "release_date": "2026-02-15",
  "language": "zh",
  "title": "vLLM-Omni 0.16.0 发布：全面升级性能与分布式能力",
  "summary": "本次更新带来...",
  "tags": ["vLLM", "多模态", "性能优化"],
  "content_md": "...",
  "generated_at": "2026-03-09T10:00:00Z",
  "source_commits": ["51dd434", "8536dce"],
  "source_prs": [1666, 1197]
}
```

## Prompt Design

### Draft Generation

**System prompt:**
- Role: vLLM-Omni technical blogger
- Audience: General AI enthusiasts
- Style: Accessible, engaging, with examples
- Language: Chinese

**User prompt includes:**
- Release info (version, date, release notes)
- Commits summary
- Issues/PRs content
- Related docs

### Platform Adaptation

**Zhihu:** Full format with proper headings, image placeholders, reference links

**Xiaohongshu:** Short format (<800 words), emoji-friendly, hashtags, cover image prompt

## Error Handling

| Scenario | Handling |
|----------|----------|
| GitHub API rate limit | Use `github_token`; retry with backoff |
| Claude API timeout | Respect `timeout_ms`; show progress |
| Release not found | List available releases |
| Invalid issue/PR number | Skip with warning |
| Doc file not found | Skip with warning |
| `publish` without draft | Error: "Run `generate` first" |
| Missing config.json | Error with template example |

## Prerequisites

**System:**
- Docker installed
- (Optional) Node.js 18+ for Xiaohongshu images

**API Keys:**
- `anthropic_auth_token` (required)
- `anthropic_base_url` (required for Zhipu)
- `github_token` (optional, recommended)
- `GOOGLE_API_KEY` (for baoyu-xhs-images)

## E2E Workflow

```bash
# 1. Setup (one-time)
cd ~/claude-code/vllm-omni-blog-generator
mkdir blogs
cat > blogs/config.json << 'EOF'
{
  "api": {
    "anthropic_auth_token": "xxx",
    "anthropic_base_url": "https://open.bigmodel.cn/api/anthropic",
    "default_model": "glm-5",
    "timeout_ms": 3000000
  },
  "github_token": "ghp_xxx",
  "default_language": "zh"
}
EOF

# 2. Build Docker image
docker build -t blog-generator .

# 3. Generate draft
docker run --rm -v $(pwd)/blogs:/app/blogs blog-generator generate \
  --release v0.16.0 --issue 1666 --pr 1197

# 4. Edit draft
vim blogs/v0.16.0/blog.md

# 5. Publish
docker run --rm -v $(pwd)/blogs:/app/blogs blog-generator publish --release v0.16.0

# 6. Generate XHS images (on host with Claude Code)
/baoyu-xhs-images blogs/v0.16.0/xiaohongshu/images/prompts.md --style tech
```

## Future Enhancements (Out of Scope for v1)

- Auto-detect new releases and notify
- Support more platforms (微信公众号, Medium)
- A/B test different blog tones
- Analytics integration
- Multi-language support beyond Chinese/English
