# Error Handling Implementation Plan

> **For Claude:** Use superpowers:executing-plans to implement task-by-task.

**Goal:** Add retry logic and graceful degradation to handle API failures.

---

## Task 1: Create retry utility module

**Files:**
- Create: `src/blog_generator/utils/__init__.py`
- Create: `src/blog_generator/utils/retry.py`

**Implementation:**
- `RetryConfig` dataclass with defaults
- `RetryExhaustedError` exception
- `async_retry` decorator with exponential backoff
- Special handling for rate limits (403)

---

## Task 2: Add RetryConfig to main config

**Files:**
- Modify: `src/blog_generator/config.py`

**Implementation:**
- Add `RetryConfig` model with defaults
- Add `retry: Optional[RetryConfig]` to `Config`

---

## Task 3: Wrap GitHub fetcher with retry

**Files:**
- Modify: `src/blog_generator/fetcher/github.py`

**Implementation:**
- Add custom exceptions: `NotFoundError`, `RateLimitError`
- Wrap `_get()` with retry decorator
- Handle 404 → `NotFoundError`, 403 → `RateLimitError`

---

## Task 4: Add FetchResult tracking and graceful degradation to CLI

**Files:**
- Modify: `src/blog_generator/cli.py`

**Implementation:**
- Add `FetchResult` dataclass to track success/failures
- Wrap PR/issue/doc/image fetches with try/except
- Skip failed resources, continue with successes
- Print summary at end
- Minimum sources check before Claude call

---

## Task 5: Add unit tests

**Files:**
- Create: `tests/test_retry.py`

**Implementation:**
- Test retry succeeds after transient failure
- Test retry exhausts after max attempts
- Test rate limit uses longer delay
