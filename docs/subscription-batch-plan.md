# Plan: YouTube Subscription Batch Summarization

## Context

Currently the tool processes one video at a time via URL. The goal is to automatically pull recent videos from YouTube subscriptions, filter them by configurable criteria (keywords + LLM-based prompt), and batch-summarize the matches. This enables a weekly workflow: run one command, get summaries of relevant subscription content.

YouTube Data API v3 with OAuth2 is required for subscription access. Quota cost is low (~1 unit per API call using `playlistItems.list` instead of `search.list` at 100 units).

## Pre-requisite: Reconcile Summarization

`main.py` has an inline Claude call (lines 96-125) with a `SUMMARY / TOP TAKEAWAYS / PROTOCOLS & INSTRUCTIONS` format. `summarizer.py` exists separately with a different format (`TLDR / KEY POINTS / PROTOCOLS/ACTION ITEMS / SUMMARY`) and is never called by `main.py`. Before adding batch mode, consolidate so both flows use one function.

**Action:** Update `summarizer.py` to use `main.py`'s prompt format, accept an `api_key` parameter, and return raw text (not parsed dict). Then have `main.py` call it. Keep `_parse_summary` for cases where structured access is needed.

## New Modules

### 1. `yt_summary/youtube_api.py` — OAuth2 + YouTube Data API

- **Credentials storage:** `~/.yt-summary/credentials.json` (client secret from Google Cloud Console), `~/.yt-summary/token.json` (auto-refreshed OAuth token)
- **Scope:** `youtube.readonly`
- **Dependencies:** `google-api-python-client`, `google-auth-oauthlib`

Functions:
- `get_credentials() -> Credentials` — Load token.json, refresh if expired, or run browser OAuth flow on first use
- `get_subscribed_channels(credentials) -> list[dict]` — Paginate `subscriptions.list(mine=True)`, return `[{channel_id, title}]`
- `get_recent_videos(credentials, channel_id, since: datetime) -> list[dict]` — Use uploads playlist trick (replace `UC` prefix with `UU`), paginate `playlistItems.list`, stop when `publishedAt < since`. Return `[{video_id, title, description, published_at, channel}]`

### 2. `yt_summary/filter.py` — Two-Stage Filtering

**Stage 1 — Keyword filter (no API cost):**
- `keyword_filter(videos, include_keywords, exclude_keywords) -> list[dict]`
- Case-insensitive substring match on title + description
- Include: video must match at least one keyword (if set)
- Exclude: video must match none

**Stage 2 — LLM filter:**
- `llm_filter(videos, filter_prompt, exclude_prompt, api_key, model) -> list[dict]`
- Batch all video metadata into one Claude call
- Supports both inclusion and exclusion criteria:
  - `filter_prompt` (inclusion): "Given these videos, return only those matching: '{filter_prompt}'"
  - `exclude_prompt` (exclusion): "Exclude any videos matching: '{exclude_prompt}'"
  - Both can be used together — inclusion is applied first, then exclusion removes from the result
- Prompt sends both criteria in a single API call, asks Claude to return a JSON array of matching video_ids
- Parse JSON response, return matching videos

### 3. `yt_summary/subscriptions.py` — Batch Orchestration

`run_subscriptions(days, include_keywords, exclude_keywords, filter_prompt, exclude_prompt, model, lang, api_key, dry_run, max_videos) -> int`

Flow:
1. Get OAuth credentials (browser auth on first run)
2. Fetch all subscribed channels
3. For each channel, fetch videos from last N days
4. Deduplicate and skip videos already cached with summaries
5. Apply keyword filter (Stage 1)
6. Apply LLM filter if filter_prompt set (Stage 2)
7. If `--dry-run`: print filtered list with channel/title/date, exit
8. Sequentially process each video: fetch transcript -> summarize -> cache
9. On per-video failure: print warning, continue to next
10. Print summary: `Processed X/Y videos (Z skipped, W errors)`

## CLI Changes in `main.py`

Convert to `argparse` subparsers:

```
python main.py "URL"                                    # backward-compat (default: summarize)
python main.py summarize "URL" --lang en --model ...    # explicit
python main.py subscriptions --days 7 --dry-run         # new
```

`subscriptions` subcommand flags:
- `--days N` (default: 7)
- `--dry-run` — preview only
- `--filter-prompt "..."` — LLM inclusion filter criteria (overrides env var)
- `--exclude-prompt "..."` — LLM exclusion filter criteria (overrides env var)
- `--include-keywords "k1,k2"` — keyword inclusion
- `--exclude-keywords "k1,k2"` — keyword exclusion
- `--max-videos N` (default: 50) — safety cap
- `--lang`, `--model` — shared with summarize

Backward compatibility: if first arg isn't a known subcommand and looks like a URL/video ID, treat as `summarize`.

## Config Changes (`config.py` + `.env.example`)

New env vars:
- `SUBSCRIPTION_FILTER_PROMPT` — default LLM inclusion filter prompt
- `SUBSCRIPTION_EXCLUDE_PROMPT` — default LLM exclusion filter prompt
- `SUBSCRIPTION_INCLUDE_KEYWORDS` — comma-separated default include keywords
- `SUBSCRIPTION_EXCLUDE_KEYWORDS` — comma-separated default exclude keywords

New functions:
- `get_subscription_filter_prompt() -> str | None`
- `get_subscription_exclude_prompt() -> str | None`
- `get_subscription_include_keywords() -> list[str]`
- `get_subscription_exclude_keywords() -> list[str]`
- `get_oauth_dir() -> Path` — returns `~/.yt-summary/`, creates if needed

## Dependencies

Add to `requirements.txt`:
```
google-api-python-client>=2.100.0
google-auth>=2.23.0
google-auth-oauthlib>=1.1.0
google-auth-httplib2>=0.1.0
```

## Files Changed

| File | Change |
|------|--------|
| `yt_summary/youtube_api.py` | **New** — OAuth2 + subscription/video fetching |
| `yt_summary/filter.py` | **New** — keyword + LLM filtering |
| `yt_summary/subscriptions.py` | **New** — batch orchestration |
| `yt_summary/summarizer.py` | Update prompt to match main.py format, add `api_key` param |
| `yt_summary/config.py` | Add subscription config getters, OAuth dir |
| `main.py` | Subparsers, call summarizer.py, add subscriptions subcommand |
| `requirements.txt` | Add google-api packages |
| `.env.example` | Add subscription config examples |
| `tests/test_youtube_api.py` | **New** — mocked OAuth + API tests |
| `tests/test_filter.py` | **New** — keyword + LLM filter tests |
| `tests/test_subscriptions.py` | **New** — batch orchestration tests |
| `tests/test_main.py` | Update for subparser backward compat |

## Implementation Order

1. Add Google API dependencies
2. Refactor `summarizer.py` to match `main.py` prompt, update `main.py` to call it
3. Create `youtube_api.py` (OAuth2 + API calls)
4. Create `filter.py` (keyword + LLM)
5. Update `config.py` with new getters
6. Create `subscriptions.py` (orchestration)
7. Refactor `main.py` CLI to subparsers
8. Update `.env.example`
9. Write tests for new modules
10. Update existing tests for refactored main.py

## OAuth Setup Guide (for user)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or use existing)
3. Enable "YouTube Data API v3" in APIs & Services
4. Create OAuth2 credentials -> Application type: "Desktop app"
5. Download the JSON file, save as `~/.yt-summary/credentials.json`
6. First run of `python main.py subscriptions` opens browser for consent
7. Token auto-refreshes on subsequent runs

## Verification

1. **Unit tests:** `pytest` — all new and existing tests pass
2. **Manual OAuth flow:** Run `python main.py subscriptions --dry-run --days 1` to verify subscription fetching works
3. **Filtering:** Run with `--filter-prompt "only technology videos" --dry-run` to verify LLM filter
4. **Full batch:** Run without `--dry-run` on a small set (`--max-videos 3 --days 1`) to verify end-to-end
5. **Backward compat:** Verify `python main.py "URL"` still works as before
6. **Code quality:** `ruff check . && ruff format --check . && mypy .`
