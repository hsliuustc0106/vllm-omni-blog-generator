---
name: pr-to-xhs
description: Generate Xiaohongshu (小红书) blog content and infographic images from a GitHub PR. Use when user provides a GitHub PR URL or asks to create XHS content from a PR.
version: 1.0.0
---

# PR to Xiaohongshu Blog Generator

Generate Xiaohongshu blog content and infographic images from a GitHub PR.

## Usage

```bash
/pr-to-xhs <github-pr-url>
/pr-to-xhs https://github.com/vllm-project/vllm-omni/pull/1689
```

## Workflow

### Step 1: Fetch PR Information

```bash
gh pr view <pr-number> --repo <owner/repo> --json title,body,author,additions,deletions,files,commits
```

### Step 2: Create Output Directory

```
blogs/pr<pr-number>/xiaohongshu/images/xhs-images/<topic-slug>/
├── source-<slug>.md          # Source content
├── analysis.md               # Content analysis
├── outline.md                # Final outline
├── post.json                 # XHS post configuration
├── prompts/                  # Image prompts
│   ├── 01-cover-<slug>.md
│   ├── 02-content-<slug>.md
│   └── ...
├── 01-cover-<slug>.png       # Generated images
├── 02-content-<slug>.png
└── ...
```

### Step 3: Analyze Content

Create `analysis.md` with:
- Content type classification (干货/种草/测评/教程)
- Core selling points
- Target audience
- Recommended XHS style and layout

### Step 4: Generate Outline

Create `outline.md` with:
- 4 images: Cover + 2 Content + Ending
- Style: notion (hand-drawn line art)
- Layout: balanced

### Step 5: Generate Images

Use glm-image skill (Zhipu AI) to generate:
1. **P1 Cover**: Hook title + visual impact
2. **P2 Core Features**: 3 key points
3. **P3 Technical Details**: Code examples, parameters
4. **P4 Ending**: CTA + GitHub link

### Step 6: Create post.json

```json
{
  "title": "<title>",
  "content": "<body with hashtags>",
  "images": ["01-cover.png", "02-content.png", ...],
  "tags": ["tag1", "tag2", ...],
  "source": {
    "type": "github_pr",
    "url": "<pr-url>",
    "pr_number": <number>
  }
}
```

## Image Generation

Default configuration:
- **Provider**: Zhipu AI (OpenAI-compatible)
- **Model**: glm-4-0520
- **Aspect Ratio**: 3:4 (Xiaohongshu optimized)
- **Quality**: 2k
- **Style**: notion (minimalist hand-drawn line art)

## Style Guidelines

### notion style elements:
- Clean light background (#FAFAFA)
- Hand-drawn line art aesthetic
- No gradients or shadows
- Simple geometric shapes
- Professional yet approachable

### Color palette:
- Background: #FAFAFA
- Main text: #1A1A1A
- Accent blue: #3B82F6
- Accent green: #10B981
- Line art: #E5E7EB

## Example

Input:
```
/pr-to-xhs https://github.com/vllm-project/vllm-omni/pull/1689
```

Output:
- `blogs/pr1689/xiaohongshu/images/xhs-images/hunyuan-image3-npu-support/`
- 4 PNG images (3:4 aspect ratio)
- post.json with title, content, tags
