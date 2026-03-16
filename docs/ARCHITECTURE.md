# Architecture

## Purpose

This repo has one primary pipeline:

1. collect source context
2. generate a draft blog
3. format it for target platforms
4. optionally generate images and assist with publishing

## Main Modules

- `src/blog_generator/cli.py`
  - Entry point for `generate`, `publish`, and helper commands
  - Orchestrates fetch, generation, formatting, and optional image/publish steps

- `src/blog_generator/config.py`
  - Loads user config from `blogs/config.json` or `/app/blogs/config.json`
  - Holds text generation, retry, and image generation config

- `src/blog_generator/fetcher/`
  - `github.py`: release, commit, PR, issue, PR-file metadata
  - `docs.py`: local or remote doc loading
  - `images.py`: image URL extraction, image loading, image embed path planning

- `src/blog_generator/generator/`
  - `claude.py`: turns collected source context into structured blog draft JSON
  - `image.py`: current API-backed image generation helper

- `src/blog_generator/formatter/`
  - `markdown.py`: saved editable draft
  - `json_fmt.py`: structured output for downstream use
  - `zhihu.py`: Zhihu-formatted content
  - `xiaohongshu.py`: Xiaohongshu content, prompt, and `post.json` helpers

- `src/blog_generator/publisher/`
  - Browser automation for Xiaohongshu posting

- `src/blog_generator/utils/`
  - shared retry logic

## Data Flow

### Generate

`generate` loads config, fetches release/PR/issue/doc/image inputs, builds a compact prompt, calls the text model, and writes:

- `blog.md`
- `blog.json`
- embedded image assets under `images/` when applicable

### Publish

`publish` reads the generated draft, creates:

- `zhihu/content.md`
- `xiaohongshu/content.md`
- `xiaohongshu/images/prompts.md`
- `xiaohongshu/post.json`

It may also generate a cover image and prepend it to the Xiaohongshu image list.

## Design Boundaries

- Fetchers should gather source data, not make formatting decisions.
- Generators should encapsulate provider-specific API calls and model prompts.
- Formatters should shape output artifacts without embedding transport logic.
- CLI code should orchestrate modules, not accumulate provider-specific logic over time.

## Existing Plans

For historical design context, see [`docs/plans`](/Users/elle/codex/vllm-omni-blog-generator/docs/plans).
