#!/usr/bin/env bash
set -e

SKILL_DIR="$HOME/.claude/skills/yt-summary"
PYTHON_BIN="$SKILL_DIR/venv/bin/python"

# Create directory structure
mkdir -p "$SKILL_DIR/scripts"
mkdir -p "$SKILL_DIR/yt_summary"

# Resolve the directory containing this script (the project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Copy skill scripts
cp "$PROJECT_ROOT/scripts/fetch_transcript.py" "$SKILL_DIR/scripts/"
cp "$PROJECT_ROOT/scripts/save_summary.py" "$SKILL_DIR/scripts/"
cp "$PROJECT_ROOT/scripts/fetch_playlist.py" "$SKILL_DIR/scripts/"

# Copy yt_summary package (excluding summarizer.py)
for f in __init__.py cache.py config.py markdown.py metadata.py playlist.py transcript.py youtube_utils.py; do
    cp "$PROJECT_ROOT/yt_summary/$f" "$SKILL_DIR/yt_summary/"
done

# Create self-contained virtualenv and install dependencies
if [ ! -f "$PYTHON_BIN" ]; then
    echo "Creating virtualenv at $SKILL_DIR/venv ..."
    python3 -m venv "$SKILL_DIR/venv"
fi
"$PYTHON_BIN" -m pip install --quiet --upgrade yt-dlp python-dotenv

# Write SKILL.md with expanded absolute paths
cat > "$SKILL_DIR/SKILL.md" <<EOF
---
name: yt-summary
description: This skill should be used when the user provides a YouTube URL or video ID and wants it summarized. Also handles YouTube playlist URLs or playlist IDs. Activate when the user says things like "summarize this video", "what's in this YouTube video", "summarize this playlist", or pastes a youtube.com or youtu.be URL.
---

Summarize the YouTube video or playlist at: \$ARGUMENTS

Follow these steps exactly:

**Step 1: Detect input type**

If the input contains \`/playlist?list=\` or starts with \`PL\`, \`UU\`, \`OL\`, \`FL\`, or \`RD\`, it is a **playlist**. Go to Step 1B.
Otherwise, it is a **single video**. Go to Step 1A.

**Step 1A: Fetch single video transcript**

Run:
\`\`\`
${PYTHON_BIN} ${SKILL_DIR}/scripts/fetch_transcript.py "\$ARGUMENTS"
\`\`\`

Parse the JSON output. If \`cached_summary\` is non-null, display it formatted and stop — do not proceed to Step 2.

Otherwise, note the \`video_id\` and \`cache_file\` values from the JSON output. Go to Step 2.

**Step 1B: Fetch playlist**

Run:
\`\`\`
${PYTHON_BIN} ${SKILL_DIR}/scripts/fetch_playlist.py "\$ARGUMENTS"
\`\`\`

Parse the JSON output. Note the \`playlist_title\` and the \`videos\` array.

For each video in the \`videos\` array:
- If \`cached_summary\` is non-null: this video is already summarized. Skip it.
- If \`needs_summary\` is true: this video needs summarization. Process it in Step 2.
- If \`error\` is present: this video failed to fetch. Note the error and skip it.

Process videos needing summarization **one at a time, sequentially**. For each video:

1. Set \`video_id\` to the video's \`video_id\` and \`cache_file\` to the video's \`cache_file\`
2. Go to Step 2 to read, summarize, and save
3. After Step 3 completes and you have verified the save succeeded, proceed to the next video

After all videos are processed, go to Step 4B.

**Step 2: Read and summarize**

Use the Read tool to read the file at the \`cache_file\` path from Step 1. Extract the transcript text from the \`## Full Transcript\` section of that file.

Using the transcript, produce a summary in exactly this format:

SUMMARY:
[A concise summary in fewer than 5 sentences]

TOP TAKEAWAYS:
- [key point]
- [key point]
- [etc.]

PROTOCOLS & INSTRUCTIONS:
[Step-by-step instructions, dosages, or specific recommendations if the video contains them. Otherwise write "None mentioned."]

**Step 3: Save to cache**

Use the Write tool to write your summary output from Step 2 to \`/tmp/yt_summary_summary.txt\`, then run:

\`\`\`
${PYTHON_BIN} ${SKILL_DIR}/scripts/save_summary.py "\$video_id" < /tmp/yt_summary_summary.txt
\`\`\`

Where \`\$video_id\` is the \`video_id\` value from the current video being processed.

**Step 4: Display (single video)**

Show the formatted summary to the user.

**Step 4B: Display (playlist)**

Show a summary of results:
- Playlist title
- Number of videos summarized in this session
- Number of videos that were already summarized (skipped)
- Number of videos that failed
- For each newly summarized video, show its title and a brief 1-line summary
EOF

# Add skill Python to ~/.claude/settings.json allowlist (global, applies in any project)
"$PYTHON_BIN" - <<PYEOF
import json
from pathlib import Path

settings_path = Path.home() / '.claude' / 'settings.json'
settings_path.parent.mkdir(parents=True, exist_ok=True)

settings = {}
if settings_path.exists():
    try:
        settings = json.loads(settings_path.read_text())
    except json.JSONDecodeError:
        pass

allow = settings.setdefault('permissions', {}).setdefault('allow', [])
entry = f"Bash({Path.home()}/.claude/skills/yt-summary/venv/bin/python:*)"
if entry not in allow:
    allow.append(entry)
    settings_path.write_text(json.dumps(settings, indent=2) + '\n')
    print(f"  Added to ~/.claude/settings.json: {entry}")
else:
    print(f"  Already in ~/.claude/settings.json allowlist")
PYEOF

echo "Installed yt-summary skill to $SKILL_DIR"
echo "Python: $PYTHON_BIN"
echo ""
echo "Usage in Claude Code: /yt-summary <youtube-url>"
