# PRD: YouTube Video Summarizer

## Overview

A command-line application that accepts a YouTube URL, downloads its transcript, and uses an LLM to generate a concise summary of the video content.

## Problem

Watching full YouTube videos is time-consuming. Users need a quick way to understand the key points of a video without watching it entirely.

## Goals

- Accept any valid YouTube video URL as input
- Extract the transcript/captions from the video
- Send the transcript to an LLM for summarization
- Return a clear, concise summary to the user
- Cache all outputs to prevent unncessary rate limit errors and cost

## Non-Goals

- No GUI or web interface (CLI only)
- No audio/video processing (transcript-only approach)
- No support for videos without captions/transcripts

## User Flow

1. User runs the application with a YouTube URL or bare video ID as an argument
2. Application validates the input and extracts/resolves the video ID
3. Application checks cache for existing transcript/summary
4. If cache miss: Application fetches the transcript (preferring manually-created captions, falling back to auto-generated)
5. If cache miss: Transcript is sent to an LLM with a summarization prompt
6. Result is cached and summary is printed to stdout

## Technical Design

### Tech Stack

- **Language:** Python 3.10+
- **Transcript extraction:** `youtube-transcript-api` library (v1.x instance API)
- **LLM integration:** Anthropic Claude API via `anthropic` Python SDK
- **CLI framework:** `argparse` (stdlib)
- **Configuration:** `python-dotenv` for `.env` file loading
- **Caching:** File-based JSON caching per video ID

### Components

1. **URL Parser** - Validates YouTube URLs/video IDs and extracts the video ID. Supports formats:
   - `https://www.youtube.com/watch?v=VIDEO_ID`
   - `https://youtu.be/VIDEO_ID`
   - `https://youtube.com/watch?v=VIDEO_ID&t=...` (with extra params)
   - Bare 11-character video IDs (e.g., `dQw4w9WgXcQ`)

2. **Transcript Fetcher** - Uses `youtube-transcript-api` to download the transcript text. Handles:
   - Language preference (default: English)
   - Fallback to auto-generated captions
   - Error reporting when no transcript is available

3. **Summarizer** - Sends transcript to Claude API with a system prompt tuned for concise video summarization. Returns a structured summary including:
   - One-line TLDR
   - Key points (bullet list)
   - Detailed summary (1-2 paragraphs)

4. **Caching Layer** - Saves transcripts and summaries to `cache/` directory as JSON files keyed by video ID. Prevents redundant API calls and reduces cost.

5. **Configuration Module** - Loads `.env` file from current directory or script directory. Provides getters for:
   - `ANTHROPIC_API_KEY` (required)
   - `CLAUDE_MODEL` (optional, defaults to `claude-sonnet-4-5-20250929`)
   - `TRANSCRIPT_LANGUAGE` (optional, defaults to `en`)

6. **CLI Interface** - Argument parsing and output formatting.

### CLI Usage

```
python main.py <url_or_id> [--lang en] [--model claude-sonnet-4-5-20250929]
```

**Arguments:**
| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `url_or_id` | Yes | - | YouTube video URL or 11-character video ID |
| `--lang` | No | From `.env` or `en` | Preferred transcript language |
| `--model` | No | From `.env` or `claude-sonnet-4-5-20250929` | Claude model to use |

**Examples:**
```bash
python main.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
python main.py "https://youtu.be/dQw4w9WgXcQ"
python main.py dQw4w9WgXcQ
python main.py dQw4w9WgXcQ --lang es --model claude-opus-4-6
```

### Configuration

The application loads configuration from a `.env` file in the current directory or script directory.

**Required:**
- `ANTHROPIC_API_KEY` - Your Anthropic API key

**Optional:**
- `CLAUDE_MODEL` - Claude model ID (default: `claude-sonnet-4-5-20250929`)
- `TRANSCRIPT_LANGUAGE` - Preferred transcript language code (default: `en`)

**Example `.env`:**
```
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-sonnet-4-5-20250929
TRANSCRIPT_LANGUAGE=en
```

### Error Handling

| Scenario | Behavior |
|----------|----------|
| Invalid URL or video ID | Print error, exit 1 |
| No transcript available | Print error, exit 1 |
| API key missing | Print error with setup instructions, exit 1 |
| LLM API failure | Print error with details, exit 1 |
| Transcript too long for context | Truncate with warning |
| Cache read/write errors | Log warning, continue without caching |

## Dependencies

**Production:**
```
anthropic>=0.39.0
youtube-transcript-api>=1.0.0,<2.0.0
python-dotenv>=1.0.0
```

**Development:**
```
pytest>=7.0.0
pytest-cov>=4.0.0
ruff>=0.0.292
mypy>=1.0.0
```

## Success Criteria

- Correctly summarizes videos with English transcripts
- Accepts both full URLs and bare video IDs
- Runs in under 30 seconds for a typical 10-minute video (first run)
- Cached summaries return instantly
- Handles common error cases gracefully with clear messages
- 100% test coverage on core modules
- Type-safe code with mypy validation

## Future Considerations (Out of Scope)

- Support for multiple languages and translation
- Batch processing of multiple URLs
- Output format options (markdown, JSON)
- Web UI or API server mode
- Playlist support
- Custom summarization prompts
- Cache expiration/management
