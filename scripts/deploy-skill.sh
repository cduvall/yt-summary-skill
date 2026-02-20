#!/usr/bin/env bash
set -e

SKILL_DIR="$HOME/.claude/skills/yt-summary"

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

# Write SKILL.md with expanded paths (not shell variables)
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
venv/bin/python ${SKILL_DIR}/scripts/fetch_transcript.py \$ARGUMENTS
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

Construct a JSON object and pipe it to the save script:
\`\`\`
echo '<json>' | venv/bin/python ${SKILL_DIR}/scripts/save_summary.py
\`\`\`

Where the JSON contains: \`video_id\`, \`title\`, \`channel\`, \`url\`, \`transcript\` (from fetch output), and \`summary\` (your output from Step 2).

**Step 4: Display**

Show the formatted summary to the user.
EOF

echo "Installed yt-summary skill to $SKILL_DIR"
echo ""
echo "If not already installed, run:"
echo "  pip install yt-dlp python-dotenv"
echo ""
echo "Usage in Claude Code: /yt-summary <youtube-url>"
