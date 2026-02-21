# CLAUDE.md

## Project Overview

YouTube transcript fetcher and cacher. Summarization is handled by the Claude Code
`yt-summary` skill reading cached transcripts — no Anthropic API key needed.

## Architecture

Modular package in `yt_summary/`, orchestrated by `main.py`:

**Flow**: validate URL → check cache → fetch transcript via yt-dlp → cache as markdown

Key modules:
- `youtube_utils.py` — URL validation, video ID extraction
- `transcript.py` — yt-dlp WebVTT fetching with retry logic
- `metadata.py` — video titles/channels, filename sanitization
- `markdown.py` — Obsidian-compatible markdown with YAML frontmatter
- `cache.py` — markdown file-based caching, channel subdirectories
- `config.py` — .env loading, Obsidian vault path
- `logging.py` — structured logging (text for CLI, JSON for Cloud Run)

### Cache Format

Obsidian-compatible markdown with YAML frontmatter (video_id, title, url, channel, cached_at).
Filename: `{video_id} – {sanitized_title}.md`, stored in `{vault_path}/{channel}/`.
Location: `OBSIDIAN_VAULT_PATH` env var, defaults to `./Summaries`.

## Commands

```bash
python main.py "https://youtu.be/VIDEO_ID"           # fetch single transcript
make test                                              # pytest
make lint                                              # ruff check + format
```

## Code Style

- PEP 8, type hints throughout, docstrings on public APIs
- `ruff` for linting and formatting
- Import order: stdlib → third-party → local (`yt_summary`)

## Rules

**ALWAYS** follow the rules in `.claude/rules/`.
