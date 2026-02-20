# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YouTube Video Summarizer: A Python CLI tool that extracts transcripts from YouTube videos and generates concise summaries using Claude API. See PRD.md for full product specifications.

## Project Structure

```
yt-summary/
├── main.py                    # CLI entry point and orchestration
├── yt_summary/                # Application package
│   ├── __init__.py
│   ├── cache.py               # Markdown-based transcript/summary caching
│   ├── config.py              # Environment and .env configuration
│   ├── markdown.py            # Markdown generation and parsing utilities
│   ├── metadata.py            # Video metadata fetching and filename sanitization
│   ├── summarizer.py          # Claude API summarization
│   ├── transcript.py          # YouTube transcript fetching (v1.x API)
│   └── youtube_utils.py       # URL validation and video ID extraction
├── tests/                     # Unit tests (pytest)
│   ├── test_cache.py
│   ├── test_config.py
│   ├── test_main.py
│   ├── test_markdown.py
│   ├── test_metadata.py
│   ├── test_summarizer.py
│   ├── test_transcript.py
│   └── test_youtube_utils.py
├── scripts/                   # Standalone utility scripts
│   └── migrate_to_markdown.py # Migration script for JSON to markdown conversion
├── cache/                     # Cached transcripts/summaries (gitignored, or custom Obsidian vault)
├── pyproject.toml             # Project config, tool settings
├── requirements.txt           # Production dependencies
└── requirements-dev.txt       # Dev dependencies
```

## Architecture

The application follows a modular, layered design:

- **CLI Layer** (`main.py`) - Argument parsing, user I/O, orchestration
- **URL Parsing** (`yt_summary/youtube_utils.py`) - YouTube URL validation and video ID extraction
- **Transcript Fetching** (`yt_summary/transcript.py`) - Downloads captions using `youtube-transcript-api` v1.x instance API
- **Metadata** (`yt_summary/metadata.py`) - Fetches video titles and sanitizes filenames
- **Summarization** (`main.py` + `yt_summary/summarizer.py`) - Interfaces with Anthropic Claude API
- **Markdown Format** (`yt_summary/markdown.py`) - Generates and parses Obsidian-compatible markdown with YAML frontmatter
- **Caching** (`yt_summary/cache.py`) - Markdown file-based caching per video ID (transcript + summary), supports Obsidian vault integration
- **Configuration** (`yt_summary/config.py`) - Loads `.env` file, provides config getters including Obsidian vault path

Flow: validate URL → check cache → fetch transcript → summarize → cache result (as markdown) → output.

### Cache Format

Cached summaries are stored as Obsidian-compatible markdown files with:
- **YAML frontmatter**: video_id, title, url, cached_at timestamp
- **Structured content**: H1 title, H2 sections for Summary, Top Takeaways, Protocols & Instructions (if present), and Full Transcript
- **Filename format**: `{video_id} – {sanitized_title}.md`
- **Storage location**: Configurable via `OBSIDIAN_VAULT_PATH` in `.env`, defaults to `./cache`

This format enables browsing, searching, and linking summaries within Obsidian while maintaining backward compatibility with JSON format (automatic migration on first access).

## Development Setup

### Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### API Configuration

```bash
# Copy template and fill in your key
cp .env.example .env
```

Required: `ANTHROPIC_API_KEY`
Optional: `CLAUDE_MODEL`, `TRANSCRIPT_LANGUAGE`, `OBSIDIAN_VAULT_PATH`

To use an Obsidian vault for cache storage, set `OBSIDIAN_VAULT_PATH` in `.env`:
```bash
OBSIDIAN_VAULT_PATH=/Users/username/Documents/Obsidian/YouTube-Summaries
```

If not set, defaults to `./cache` directory.

## Common Commands

## Rules
- **ALWAYS** use the rules laid out in `.claude/rules/`

### Running the Application

```bash
python main.py "https://www.youtube.com/watch?v=VIDEO_ID"
python main.py "https://youtu.be/VIDEO_ID" --lang en
python main.py "https://youtube.com/watch?v=VIDEO_ID" --model claude-sonnet-4-5-20250929
```

### Testing

```bash
pytest                          # Run all tests
pytest --cov                    # With coverage
pytest tests/test_transcript.py # Single file
pytest -k "test_valid_urls"     # Pattern match
```

## Key Dependencies

- `anthropic` - Claude API client
- `youtube-transcript-api` v1.x - Extract captions from YouTube (instance-based API)
- `python-dotenv` - Load `.env` files
- `pytest` - Testing framework
- `ruff` - Linting and formatting

## Testing Strategy

Unit tests cover:
- URL parsing (valid/invalid formats, edge cases)
- Transcript fetching (mock API responses, language fallbacks)
- Metadata fetching (video titles, filename sanitization)
- Markdown generation and parsing (frontmatter, sections, round-trip conversion)
- Summarization (mock LLM responses, prompt construction)
- Caching (markdown format, cached summary reuse, JSON-to-markdown migration)
- Configuration (Obsidian vault path validation, environment variables)
- Error handling (missing transcripts, API failures, missing API key, invalid paths)

All tests mock external APIs (YouTube, Anthropic) to avoid quota/cost issues. Tests achieve 99% coverage (missing line is documented dead code).

## Error Handling

Exit codes: 0 for success, 1 for any error. Errors include:
- Invalid URL format
- Video has no transcript available
- Missing or invalid ANTHROPIC_API_KEY
- API rate limits or failures

## Code Style

- Follow PEP 8
- Use type hints throughout
- Docstrings for public functions and classes
- Use `ruff` for consistent formatting
- Organize imports: stdlib → third-party → local (`yt_summary`)
