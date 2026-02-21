# yt-summary

A Claude Code skill that summarizes YouTube videos — no API key required for summarization. It fetches the transcript, then uses your Claude Code subscription to generate the summary and caches results locally as Obsidian-compatible markdown.

Also ships a standalone CLI (`main.py`) for use outside Claude Code, which does require an Anthropic API key.

## Prerequisites

- [Claude Code](https://claude.ai/code) with a Max subscription
- Python 3.10+
- `yt-dlp` and `python-dotenv`:
  ```bash
  pip install yt-dlp python-dotenv
  ```

## Install the skill

```bash
git clone https://github.com/cduvall/yt-summary-skill.git
cd yt-summary-skill
bash scripts/deploy-skill.sh
```

This copies the skill and supporting scripts to `~/.claude/skills/yt-summary/`.

## Usage

In any Claude Code session:

```
/yt-summary https://www.youtube.com/watch?v=VIDEO_ID
/yt-summary https://youtu.be/VIDEO_ID
```

Claude fetches the transcript, summarizes it, saves the result to your configured cache directory, and displays the summary. Running the same URL again returns the cached summary instantly.

## Configuration

Copy the example env file and edit as needed:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `OBSIDIAN_VAULT_PATH` | CWD | Where to store summary markdown files |
| `TRANSCRIPT_LANGUAGE` | `en` | Preferred transcript language code |
| `YOUTUBE_COOKIES_FILE` | (optional) | Netscape cookie file for yt-dlp authentication |

The `.env` file should live in the directory where you run Claude Code, or in the project root.

## Cache format

Summaries are saved as Obsidian-compatible markdown with YAML frontmatter:

```
{OBSIDIAN_VAULT_PATH}/Summaries/{Channel Name}/{Video Title} [{video_id}].md
```

Each file includes the summary, top takeaways, protocols/instructions (if applicable), and full transcript. Fields like `read` and `starred` in the frontmatter are editable in Obsidian and preserved on subsequent runs.

## Standalone CLI

If you want to use this outside Claude Code (requires `ANTHROPIC_API_KEY`):

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python main.py "https://www.youtube.com/watch?v=VIDEO_ID"
python main.py "https://youtu.be/VIDEO_ID" --lang es
python main.py "URL" --model claude-opus-4-6
```

## License

MIT
