# Image Providers

## Current State

The repo currently includes provider-backed image generation in:

- [`src/blog_generator/generator/image.py`](/Users/elle/codex/vllm-omni-blog-generator/src/blog_generator/generator/image.py)

The current publish flow uses provider-backed cover generation and then updates:

- `blogs/<name>/xiaohongshu/images/cover.png`
- `blogs/<name>/xiaohongshu/post.json`

## Integration Principles

- Keep image API calls inside `generator/` helpers, not scattered through CLI code.
- Keep provider config in `config.py`.
- Keep prompt construction in formatters or dedicated prompt helpers.
- Keep publish behavior provider-agnostic where possible.

## Expected Failure Mode

Image generation is optional in the publish flow.

Preferred behavior:

- warn clearly on provider failure
- continue publish without a cover image
- preserve manual fallback workflows

## Provider Migration Guidance

When replacing or adding a provider:

1. add or update a dedicated generator helper
2. keep environment variables and config explicit
3. update tests for happy path and graceful failure
4. avoid mixing API-specific payload logic into `formatter/` or `publisher/`

## Current Repository Context

- GLM-backed image generation is already integrated in the app
- Gemini Web API image generation currently exists as a Codex skill, not as a runtime app integration

That distinction matters:

- a Codex skill helps the agent perform a task during a session
- the Python app still needs normal code integration if it must call Gemini automatically during `publish`
