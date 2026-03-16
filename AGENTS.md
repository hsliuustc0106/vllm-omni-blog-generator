# AGENTS.md

## Purpose

This repo generates technical blog posts for vLLM-Omni, formats them for publishing, and supports Xiaohongshu automation plus cover image generation.

Use this file as the entrypoint for agent work in the repo. Keep it short. Read deeper docs only when the task needs them.

## Repo Map

- Source code: [`src/blog_generator`](/Users/elle/codex/vllm-omni-blog-generator/src/blog_generator)
- Tests: [`tests`](/Users/elle/codex/vllm-omni-blog-generator/tests)
- Design and implementation plans: [`docs/plans`](/Users/elle/codex/vllm-omni-blog-generator/docs/plans)
- Runtime outputs and user config: `blogs/` or `/app/blogs/`

## Read These Next

- Architecture overview: [`docs/ARCHITECTURE.md`](/Users/elle/codex/vllm-omni-blog-generator/docs/ARCHITECTURE.md)
- Command and output workflows: [`docs/WORKFLOWS.md`](/Users/elle/codex/vllm-omni-blog-generator/docs/WORKFLOWS.md)
- Image provider notes: [`docs/IMAGE_PROVIDERS.md`](/Users/elle/codex/vllm-omni-blog-generator/docs/IMAGE_PROVIDERS.md)

## Core Rules

- Prefer minimal, targeted changes. Do not refactor unrelated code while touching a workflow.
- Preserve existing CLI behavior and output paths unless the task explicitly changes them.
- Keep provider-specific code isolated under `generator/`, `formatter/`, or config models instead of spreading it through the CLI.
- `generate` and `publish` are separate phases. Do not assume publish-time files exist during generate.
- Treat `blogs/` as runtime data, not source code. Avoid editing user-generated outputs unless the task is specifically about them.
- Keep graceful degradation where it already exists. Optional fetch/image failures should generally warn and continue, not abort the entire publish flow.
- Do not hardcode secrets or API keys. Use config files and environment variables.

## Testing

Run `pytest -q` after non-trivial changes.

If touching image generation, publish, or Xiaohongshu formatting, also check:

- `pytest -q tests/generator/test_image.py`
- `pytest -q tests/test_publish_image_integration.py`
- `pytest -q tests/test_xiaohongshu_formatter.py`

If touching fetch or generation flow, read the relevant tests first and add coverage when behavior changes.

## Current Hot Spots

- `src/blog_generator/cli.py`: command orchestration and publish flow
- `src/blog_generator/generator/claude.py`: blog text generation
- `src/blog_generator/generator/image.py`: current provider-backed cover generation
- `src/blog_generator/formatter/xiaohongshu.py`: title, prompt, and `post.json` shaping
- `src/blog_generator/publisher/xiaohongshu.py`: browser automation for posting

## When Unsure

- Prefer preserving output file names and directory layout.
- Prefer reading tests and the focused docs above over adding more top-level instructions here.
- If a task changes user workflow semantics, document it in `docs/` and update tests.
