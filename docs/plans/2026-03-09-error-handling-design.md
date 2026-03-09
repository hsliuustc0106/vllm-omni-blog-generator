# Error Handling & Resilience Design

## Overview

Add robust error handling to the blog generator to handle API failures gracefully, preventing lost work and improving user experience when things go wrong.

**Target failures:**
- GitHub rate limits (403)
- GitHub 404s (missing PRs/issues/docs)
- Claude API timeouts
- Network transient errors (connection drops, DNS failures)

**Approach:** Retry with exponential backoff + graceful degradation (skip failed resources, continue with what works).

---

## Section 1: Retry Mechanism

**New module:** `src/blog_generator/utils/retry.py`

### Retry Decorator

```python
@retry(
    max_attempts=3,
    base_delay=1.0,        # Exponential: 1s, 2s, 4s
    max_delay=30.0,
    retryable_errors=[httpx.TimeoutException, httpx.NetworkError],
)
async def fetch_with_retry(client, url): ...
```

### Retry Behavior by Error Type

| Error Type | Action |
|------------|--------|
| Timeout/Network | Retry with exponential backoff |
| GitHub 403 (rate limit) | Retry with longer delay (honor `Retry-After` header if present) |
| GitHub 404 | No retry - raise immediately for graceful handling |
| GitHub 5xx | Retry |
| Claude timeout | Retry (existing 50min timeout in config) |
| Claude API error | Retry on 529 (overloaded), no retry on 400/401 |

### Key Implementation

- Async-compatible decorator
- Log each retry attempt with delay
- Configurable via `config.json` (optional override)

---

## Section 2: Graceful Degradation

**Modified files:** `cli.py`, `fetcher/github.py`

### Strategy

Collect what succeeds, skip what fails, always produce output (unless minimum requirements not met).

```python
# Current behavior (fails fast):
pr_data = await github.get_pr(client, pr_num)  # One failure kills entire run

# New behavior (collect successes):
pr_data = []
failed_prs = []
for pr_num in prs:
    try:
        pr_data.append(await github.get_pr_with_retry(client, pr_num))
    except NotFoundError:
        failed_prs.append(pr_num)
        console.print(f"[yellow]⚠[/yellow] PR #{pr_num} not found, skipping")
    except RetryExhaustedError as e:
        failed_prs.append(pr_num)
        console.print(f"[yellow]⚠[/yellow] PR #{pr_num} failed after retries: {e}")
```

### Scope of Graceful Handling

| Resource | On Failure | Result |
|----------|------------|--------|
| Release fetch | **Hard fail** | Can't generate without release info |
| Commit fetch | Skip, warn | Generate without commit context |
| PR fetch | Skip, warn | Generate without that PR |
| Issue fetch | Skip, warn | Generate without that issue |
| Doc fetch | Skip, warn | Generate without that doc |
| Image fetch | Skip, warn | Generate without that image |
| Claude generation | **Hard fail** | No blog without LLM output |

### Minimum Requirements Check

```python
# Before calling Claude API
if not release_info and not pr_data:
    console.print("[red]Error: No content sources available[/red]")
    raise typer.Exit(1)
```

---

## Section 3: Error Reporting & Logging

**Goal:** Clear, actionable messages that help users understand what happened and what to do.

### Message Examples

| Scenario | Current | Improved |
|----------|---------|----------|
| GitHub 404 | `ValueError: Release v0.99 not found` | `[!] Release v0.99 not found. Available: v0.16.0, v0.15.0 (use --latest or specify valid version)` |
| GitHub rate limit | `httpx.HTTPStatusError: 403` | `[!] GitHub rate limit hit. Waiting 60s... (set github_token in config for higher limits)` |
| Claude timeout | `ReadTimeout` | `[!] Claude API timeout after 50min. Try reducing context or check API status` |
| Network error | `ConnectError` | `[!] Network error: unable to reach github.com. Check connection or try again` |
| All PRs failed | (no message) | `[!] Warning: 0/3 PRs fetched. Blog may lack context. Check PR numbers exist.` |

### Summary Output

At end of run, print summary of what succeeded/failed:

```
✓ Blog generated: blogs/v0.16.0/blog.md

Sources used:
  ✓ Release v0.16.0
  ✓ 2/3 PRs (#1197, #1652)
  ⚠ 1 PR skipped (#999 - not found)
  ✓ 1/2 docs (architecture.md)
  ⚠ 1 doc skipped (missing.md - 404)
```

### Implementation

- Add `FetchResult` dataclass to track success/failure per resource type
- Print summary before saving output
- Keep existing Rich console formatting

---

## Section 4: Configuration

**Extend `config.json` with optional retry settings:**

```json
{
  "api": { ... },
  "github_token": "ghp_xxx",
  "default_language": "zh",
  "retry": {
    "max_attempts": 3,
    "base_delay_ms": 1000,
    "max_delay_ms": 30000,
    "rate_limit_delay_ms": 60000
  }
}
```

### Defaults (if not specified)

```python
DEFAULT_RETRY = RetryConfig(
    max_attempts=3,
    base_delay_ms=1000,       # 1s
    max_delay_ms=30000,       # 30s max
    rate_limit_delay_ms=60000,  # 60s for rate limits
)
```

### Backward Compatibility

- All retry settings optional
- Existing configs work without changes
- Sensible defaults for all users

---

## Section 5: Testing Strategy

### Unit Tests (Mocked API Responses)

| Test | What it verifies |
|------|------------------|
| `test_retry_success_after_failure` | Retry recovers from transient error |
| `test_retry_exhausted` | Fails after max attempts |
| `test_skip_missing_pr` | 404 PR is skipped, not fatal |
| `test_rate_limit_backoff` | Uses longer delay on 403 |
| `test_minimum_sources_check` | Fails when all sources exhausted |

### Integration Tests (Optional, Real API Calls)

```bash
# Test with invalid PR (should skip)
blog-generator generate --release v0.16.0 --pr 999999

# Test rate limit simulation (mocked)
pytest tests/test_retry.py -k rate_limit
```

### Manual Testing Checklist

- [ ] Disconnect network mid-run → clear error message
- [ ] Invalid release tag → lists available releases
- [ ] Mix valid + invalid PRs → generates with valid ones only
- [ ] GitHub token missing → still works (lower rate limit)
- [ ] Claude timeout → retry with backoff, clear final error

---

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/blog_generator/utils/__init__.py` | Create | Utils package |
| `src/blog_generator/utils/retry.py` | Create | Retry decorator and helpers |
| `src/blog_generator/config.py` | Modify | Add RetryConfig model |
| `src/blog_generator/fetcher/github.py` | Modify | Add retry-wrapped fetch methods |
| `src/blog_generator/cli.py` | Modify | Graceful degradation + summary output |
| `tests/test_retry.py` | Create | Unit tests for retry logic |
| `tests/test_cli_resilience.py` | Create | Integration tests for graceful degradation |

---

## Out of Scope

- Caching (can be added later)
- Circuit breaker pattern
- Checkpointing/resume (overkill for this use case)
- JSON parsing improvements (not a reported issue)
