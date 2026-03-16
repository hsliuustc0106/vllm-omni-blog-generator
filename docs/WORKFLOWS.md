# Workflows

## Generate

`blog-generator generate` creates a draft from one or more source types:

- release
- PRs
- issues
- docs
- images

Typical outputs:

- `blogs/<release-or-pr-suffix>/blog.md`
- `blogs/<release-or-pr-suffix>/blog.json`
- `blogs/<release-or-pr-suffix>/images/*` when embedded images are loaded

Important notes:

- Release mode and PR-only mode are both supported.
- Missing optional sources should usually warn and continue.
- If no valid content sources remain, generation should fail clearly.

## Publish

`blog-generator publish --release <name>` transforms the approved draft into platform artifacts.

Typical outputs:

- `blogs/<name>/zhihu/content.md`
- `blogs/<name>/xiaohongshu/content.md`
- `blogs/<name>/xiaohongshu/images/prompts.md`
- `blogs/<name>/xiaohongshu/post.json`

Important notes:

- `publish` depends on `blog.json` and `blog.md` already existing.
- Xiaohongshu output has stricter title and image handling than the editable draft.
- Cover image generation should not block publish if it fails.

## Xiaohongshu Image Flow

There are two related but different image workflows:

1. publish-time cover generation
2. prompt-file-based image generation from `xiaohongshu/images/prompts.md`

Do not conflate them. A change to cover generation should not silently break prompt-file workflows.

## Runtime Data

The `blogs/` directory is user/runtime data:

- config
- generated drafts
- generated platform content
- generated images

Do not treat these as source files for refactors or repository cleanup.

## Safe Changes

Usually safe:

- adding tests
- improving prompt compaction
- isolating provider logic
- improving retry/error messages

Higher risk:

- changing output filenames
- changing directory layout
- changing `post.json` structure
- moving provider calls directly into unrelated modules
