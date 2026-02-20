# YouTube Video Summarizer

A command-line tool that downloads transcripts from YouTube videos and generates concise summaries using Claude AI.

## Features

- Extract transcripts from any YouTube video with captions
- Generate structured summaries including TLDR, key points, and detailed summary
- Support for multiple languages (with fallback to auto-generated captions)
- Configurable Claude models
- Clear error messages and helpful guidance

## Installation

1. Clone the repository and navigate to the directory:
```bash
cd yt-summary
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Setup

You need an Anthropic API key to use this application. Get one from [console.anthropic.com](https://console.anthropic.com).

### Option 1: Using .env file (Recommended)

1. Copy the example file:
```bash
cp .env.example .env
```

2. Edit `.env` and add your API key:
```
ANTHROPIC_API_KEY=your-api-key-here
```

The application will automatically load these variables when it runs.

### Option 2: Using environment variables

Set the API key directly as an environment variable:
```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

## Configuration

You can configure the application in three ways (in order of precedence):

1. **Command-line arguments** - Override everything
   ```bash
   python main.py "URL" --lang es --model claude-opus-4-6
   ```

2. **.env file** - Default values for your project
   ```
   ANTHROPIC_API_KEY=your-key
   CLAUDE_MODEL=claude-opus-4-6
   TRANSCRIPT_LANGUAGE=es
   ```

3. **Defaults** - Built-in fallbacks
   - Model: `claude-sonnet-4-5-20250929`
   - Language: `en`

## Usage

Basic usage:
```bash
python main.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

With command-line options:
```bash
# Specify transcript language
python main.py "https://youtu.be/VIDEO_ID" --lang es

# Use a specific Claude model
python main.py "https://youtube.com/watch?v=VIDEO_ID" --model claude-opus-4-6

# Override .env defaults
python main.py "URL" --lang fr --model claude-opus-4-6
```

Supported YouTube URL formats:
- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://youtube.com/watch?v=VIDEO_ID&t=...` (with extra parameters)

## Output

The application produces a formatted summary with:

```
============================================================
VIDEO SUMMARY
============================================================

TLDR: One-line summary of the video content

KEY POINTS:
  • Key point 1
  • Key point 2
  • Key point 3

SUMMARY:
Detailed 1-2 paragraph summary of the video content.

============================================================
```

## Development

### Setup development environment

```bash
pip install -r requirements-dev.txt
```

### Running tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Run a specific test file
pytest tests/test_youtube_utils.py

# Run tests matching a pattern
pytest -k "test_valid"

## Project Structure

- `main.py` - CLI entry point and orchestration
- `yt_summary/` - Application package
  - `cache.py` - Markdown-based caching
  - `config.py` - Environment configuration
  - `markdown.py` - Markdown generation and parsing
  - `metadata.py` - Video metadata fetching
  - `summarizer.py` - Claude API integration
  - `transcript.py` - Transcript fetching
  - `youtube_utils.py` - URL parsing and validation
- `tests/` - Comprehensive test suite
- `Makefile` - Development convenience targets
- `requirements.txt` - Production dependencies
- `requirements-dev.txt` - Development dependencies
- `pyproject.toml` - Project configuration and tool settings

## Error Handling

The application provides clear error messages for:
- **Invalid URLs** - Shows supported YouTube URL formats
- **Missing transcripts** - Videos without captions cannot be summarized
- **Missing API key** - Explains how to set `ANTHROPIC_API_KEY`
- **API errors** - Displays error details from the Claude API

Exit code 0 indicates success, exit code 1 indicates any error.

## Environment Variables

The application reads configuration from `.env` file or environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | (required) | API key from console.anthropic.com |
| `CLAUDE_MODEL` | claude-sonnet-4-5-20250929 | Claude model to use |
| `TRANSCRIPT_LANGUAGE` | en | Transcript language code (e.g., es, fr, de) |
| `OBSIDIAN_VAULT_PATH` | (optional) | Path to Obsidian vault for cache storage |
| `YOUTUBE_COOKIES_FILE` | (optional) | Path to Netscape cookie file for yt-dlp auth |
| `OAUTH_DIR` | (optional) | Directory containing OAuth token/credentials files |

## Limitations

- Requires videos to have captions (manually created or auto-generated)
- Transcript length is limited by Claude's context window
- Output quality depends on transcript accuracy and Claude model capabilities
- API costs apply for each summarization request

## License

MIT
