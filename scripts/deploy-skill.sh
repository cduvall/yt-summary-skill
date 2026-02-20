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

# Copy yt_summary package (excluding summarizer.py)
for f in __init__.py cache.py config.py markdown.py metadata.py transcript.py youtube_utils.py; do
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
description: This skill should be used when the user provides a YouTube URL or video ID and wants it summarized. Activate when the user says things like "summarize this video", "what's in this YouTube video", or pastes a youtube.com or youtu.be URL.
---

Summarize the YouTube video at: \$ARGUMENTS

Follow these steps exactly:

**Step 1: Fetch transcript**

Run:
\`\`\`
${PYTHON_BIN} ${SKILL_DIR}/scripts/fetch_transcript.py \$ARGUMENTS
\`\`\`

Parse the JSON output. If \`cached_summary\` is non-null, display it formatted and stop — do not proceed to Step 2.

**Step 2: Summarize**

Using the \`transcript\` field from the JSON, produce a summary in exactly this format:

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
${PYTHON_BIN} ${SKILL_DIR}/scripts/save_summary.py < /tmp/yt_summary_summary.txt
\`\`\`

The script reads video metadata and the transcript automatically from a temp file written by Step 1.

**Step 4: Display**

Show the formatted summary to the user.
EOF

echo "Installed yt-summary skill to $SKILL_DIR"
echo "Python: $PYTHON_BIN"
echo ""
echo "Usage in Claude Code: /yt-summary <youtube-url>"
