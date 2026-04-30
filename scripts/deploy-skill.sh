#!/usr/bin/env bash
set -e

SKILL_DIR="$HOME/.claude/skills/yt-summary"
MDFLOW_SKILL_DIR="$HOME/.claude/skills/yt-summary-mdflow"
PYTHON_BIN="$SKILL_DIR/venv/bin/python"

# Resolve the directory containing this script (the project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# ---------------------------------------------------------------------------
# Read mdFlow config from project .env (required for mdFlow SKILL.md)
# ---------------------------------------------------------------------------
ENV_FILE="$PROJECT_ROOT/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: $ENV_FILE not found." >&2
    echo "See docs/mdflow-storage.md for setup instructions." >&2
    exit 1
fi

MDFLOW_STREAM_ID=$(grep -E '^MDFLOW_STREAM_ID=' "$ENV_FILE" | cut -d= -f2- | tr -d '[:space:]')
MDFLOW_ROOT_PARENT_ID=$(grep -E '^MDFLOW_ROOT_PARENT_ID=' "$ENV_FILE" | cut -d= -f2- | tr -d '[:space:]')

if [ -z "$MDFLOW_STREAM_ID" ]; then
    echo "ERROR: MDFLOW_STREAM_ID is not set in $ENV_FILE." >&2
    echo "See docs/mdflow-storage.md for setup instructions." >&2
    exit 1
fi

if [ -z "$MDFLOW_ROOT_PARENT_ID" ]; then
    echo "ERROR: MDFLOW_ROOT_PARENT_ID is not set in $ENV_FILE." >&2
    echo "See docs/mdflow-storage.md for setup instructions." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Create shared directory structure under yt-summary (canonical install)
# ---------------------------------------------------------------------------
mkdir -p "$SKILL_DIR/scripts"
mkdir -p "$SKILL_DIR/yt_summary"

# Copy skill scripts
cp "$PROJECT_ROOT/scripts/fetch_transcript.py" "$SKILL_DIR/scripts/"
cp "$PROJECT_ROOT/scripts/save_summary.py" "$SKILL_DIR/scripts/"
cp "$PROJECT_ROOT/scripts/check_summary_complete.py" "$SKILL_DIR/scripts/"

# Copy yt_summary package (excluding summarizer.py)
for f in __init__.py cache.py config.py markdown.py metadata.py transcript.py youtube_utils.py; do
    cp "$PROJECT_ROOT/yt_summary/$f" "$SKILL_DIR/yt_summary/"
done

# Create self-contained virtualenv and install dependencies
if [ ! -f "$PYTHON_BIN" ]; then
    echo "Creating virtualenv at $SKILL_DIR/venv ..."
    python3.10 -m venv "$SKILL_DIR/venv"
fi
"$PYTHON_BIN" -m pip install --quiet --upgrade yt-dlp python-dotenv

# ---------------------------------------------------------------------------
# Write yt-summary SKILL.md (original skill, unchanged behavior)
# ---------------------------------------------------------------------------
cat > "$SKILL_DIR/SKILL.md" <<EOF
---
name: yt-summary
description: Fetches and summarizes YouTube videos. Use when the user provides a YouTube URL or video ID, says "summarize this video", or pastes a youtube.com/youtu.be link.
---

Summarize the YouTube video at: \$ARGUMENTS

Follow these steps exactly:

**Step 1: Fetch transcript**

Run:
\`\`\`
${PYTHON_BIN} ${SKILL_DIR}/scripts/fetch_transcript.py "\$ARGUMENTS"
\`\`\`

Parse the JSON output. If \`cached_summary\` is non-null, display it formatted and stop — do not proceed to Step 2.

Otherwise, note the \`video_id\` and \`cache_file\` values from the JSON output.

**Step 2: Summarize**

The \`transcript\` field in the JSON output contains the full transcript text. Use it directly.

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

Run:
\`\`\`
${PYTHON_BIN} ${SKILL_DIR}/scripts/save_summary.py "\$video_id" <<'SUMMARY'
[your summary output from Step 2]
SUMMARY
\`\`\`

Where \`\$video_id\` is the \`video_id\` value from Step 1's JSON output.

**Step 4: Display**

Show the formatted summary to the user.
EOF

# ---------------------------------------------------------------------------
# Set up yt-summary-mdflow skill directory (shares venv+scripts+package via
# symlinks — both skills operate on the same local transcript/summary cache)
# ---------------------------------------------------------------------------
mkdir -p "$MDFLOW_SKILL_DIR"

# Symlink the shared components so both skills use one copy
for target in venv scripts yt_summary; do
    link="$MDFLOW_SKILL_DIR/$target"
    if [ -L "$link" ] || [ -e "$link" ]; then
        rm -rf "$link"
    fi
    ln -s "$SKILL_DIR/$target" "$link"
done

# ---------------------------------------------------------------------------
# Write yt-summary-mdflow SKILL.md (IDs baked in from .env at deploy time)
# ---------------------------------------------------------------------------
cat > "$MDFLOW_SKILL_DIR/SKILL.md" <<EOF
---
name: yt-summary-mdflow
description: Fetches and summarizes YouTube videos, then stores the summary and transcript in mdFlow. Use when the user provides a YouTube URL or video ID and wants it saved to mdFlow.
---

Summarize the YouTube video at: \$ARGUMENTS

Follow these steps exactly:

**Step 1: Switch to the YouTube Summaries stream**

Call: \`mcp__claude_ai_MDFlow_Secure__switch_stream\` with \`stream_id=${MDFLOW_STREAM_ID}\`

This must be the Knowledge stream named "YouTube Summaries".

**Step 2: Extract the video_id**

Run:
\`\`\`
${PYTHON_BIN} ${SKILL_DIR}/scripts/fetch_transcript.py --id-only "\$ARGUMENTS"
\`\`\`

Capture stdout as \`video_id\`. If the command exits non-zero, report the error and stop.

**Step 3: Look for an existing transcript note in mdFlow**

Call: \`mcp__claude_ai_MDFlow_Secure__search_items\` with query \`"\$video_id Transcript"\`

From the results, find a non-archived item of \`type=note\` whose \`title\` exactly equals \`\$video_id Transcript\` (e.g., \`dQw4w9WgXcQ Transcript\`). Archived items may appear in results — filter them out (status must NOT be \`"archived"\`).

If such an item is found:
- Capture its \`id\` as \`transcript_id\`.
- Capture its \`parent\` as \`summary_note_id\`.

If no such item is found, \`transcript_id\` and \`summary_note_id\` are null.

**Step 4: If transcript found — check summary completeness**

If \`summary_note_id\` is not null:

Call: \`mcp__claude_ai_MDFlow_Secure__get_item\` with \`id=\$summary_note_id\`

Write the returned \`body\` into a heredoc and pipe it to the completeness checker:

\`\`\`
\${PYTHON_BIN} \${SKILL_DIR}/scripts/check_summary_complete.py <<'BODY'
[the summary note body verbatim]
BODY
\`\`\`

Check the exit code:

- Exit code **0** → summary is complete → display it to the user and **stop**. No transcript fetch happens.
- Exit code **non-zero** → summary is incomplete (Case B): proceed below.

**If the summary is incomplete** (Case B):

- Call: \`mcp__claude_ai_MDFlow_Secure__get_item\` with \`id=\$transcript_id\` to load the existing transcript note.
- Recover the transcript text from the returned \`body\` by stripping the leading YAML frontmatter:
  - If the body starts with \`---\n\`, find the next line that is exactly \`---\`, and take everything after that closing \`---\` (skipping a single blank line after it if present).
  - If the body does not start with \`---\`, use the body as-is.
- Using the recovered transcript, produce a summary in exactly this format (use markdown headings):

## Title Evaluation
[1–3 sentences: does the content actually deliver on the title? If the title promises "the ONE thing" or "top 3 tricks", make those obvious in the summary below. Acknowledge a misleading title if true.]

## Summary
[≤5 sentences]

## Top Takeaways
- [key point]
- [key point]
- [etc.]

## Protocols & Instructions
[Step-by-step instructions, dosages, or specific recommendations if the video contains them. Otherwise write "None mentioned."]

- Build the new summary-note body: preserve the **existing summary note's YAML frontmatter** (everything in the existing summary body up to and including the closing \`---\`), then replace the markdown body below it with the newly generated summary.
- Call: \`mcp__claude_ai_MDFlow_Secure__update_item\` with \`id=\$summary_note_id\` and the new \`body\`.
- Display the summary to the user and **stop**. No \`fetch_transcript.py\` call happens in Case B.

**Step 5: Fetch transcript (Case C only — transcript not in mdFlow)**

This step is reached only when \`transcript_id\` is null (no transcript note found in mdFlow in Step 3).

Run:
\`\`\`
${PYTHON_BIN} ${SKILL_DIR}/scripts/fetch_transcript.py "\$ARGUMENTS"
\`\`\`

Parse the JSON output. Note the \`video_id\` (re-confirm), \`title\`, \`channel\`, \`url\`, and \`transcript\` values.

Do NOT short-circuit on \`cached_summary\` — ignore that field in this skill. mdFlow is the source of truth.

The script also caches locally as a side effect — that is fine.

**Step 6: Generate summary (Case C)**

Using the \`transcript\` from Step 5, produce a summary in exactly this format (use markdown headings):

## Title Evaluation
[1–3 sentences: does the content actually deliver on the title? If the title promises "the ONE thing" or "top 3 tricks", make those obvious in the summary below. Acknowledge a misleading title if true.]

## Summary
[≤5 sentences]

## Top Takeaways
- [key point]
- [key point]
- [etc.]

## Protocols & Instructions
[Step-by-step instructions, dosages, or specific recommendations if the video contains them. Otherwise write "None mentioned."]

**Step 7: Persist (Case C)**

Save locally (backup copy):

\`\`\`
${PYTHON_BIN} ${SKILL_DIR}/scripts/save_summary.py "\$video_id" <<'SUMMARY'
[your full summary output above]
SUMMARY
\`\`\`

Look up the channel area:

Call: \`mcp__claude_ai_MDFlow_Secure__list_items\` with \`parent=${MDFLOW_ROOT_PARENT_ID}\`

From the results, find an item whose \`title\` exactly matches the \`channel\` value from Step 5 AND whose \`status\` is NOT \`"archived"\`. Archived items are returned by list_items — you must filter them out.

If a matching non-archived item is found, capture its \`id\` as \`channel_id\`. Otherwise, \`channel_id\` is null (channel does not exist yet).

Build the note title:
- Take the first 100 characters of the video title.
- If truncation falls mid-word (i.e., the character at position 100 is not a space and there is a character after position 100), back off to the previous word boundary (the last space before position 100).
- Trim any trailing whitespace.
- Append \` [\$video_id]\`.

Build the YAML frontmatter block to prepend to both the summary note and transcript subnote:

\`\`\`
---
video_id: \$video_id
title: \$title
channel: \$channel
url: \$url
cached_at: <today's date YYYY-MM-DD>
---
\`\`\`

The summary note body = frontmatter block + full summary text generated above.

The transcript subnote title is: \`\$video_id Transcript\`
The transcript subnote body = frontmatter block + full transcript text from Step 5.

**Case C-A — channel area already exists (\`channel_id\` is not null):**

Call \`mcp__claude_ai_MDFlow_Secure__bulk_create_items\` with items structured as:
- Top-level item: summary note with \`parent=<channel_id>\`, \`type=note\`, \`status=living\`, \`tags=["youtube","summary"]\`, body = summary note body.
  - Its \`children\`: one transcript subnote with \`type=note\`, \`status=living\`, \`tags=["youtube","transcript"]\`, body = transcript subnote body.

**Case C-B — channel area does not exist (\`channel_id\` is null):**

Call \`mcp__claude_ai_MDFlow_Secure__bulk_create_items\` with items structured as:
- Top-level item: channel area with \`parent=${MDFLOW_ROOT_PARENT_ID}\`, \`type=area\`, \`status=living\`, \`title=<channel name>\`.
  - Its \`children\`: one summary note with \`type=note\`, \`status=living\`, \`tags=["youtube","summary"]\`, body = summary note body.
    - Its \`children\`: one transcript subnote with \`type=note\`, \`status=living\`, \`tags=["youtube","transcript"]\`, body = transcript subnote body.

**Step 8: Display**

Show the formatted summary to the user.
EOF

# ---------------------------------------------------------------------------
# Add skill Python to ~/.claude/settings.json allowlist
# (yt-summary-mdflow shares the same venv, so one entry covers both skills)
# ---------------------------------------------------------------------------
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

echo ""
echo "Installed yt-summary skill to $SKILL_DIR"
echo "Installed yt-summary-mdflow skill to $MDFLOW_SKILL_DIR"
echo "  (mdflow skill shares venv+scripts+package via symlinks)"
echo "Python: $PYTHON_BIN"
echo "mdFlow stream: ${MDFLOW_STREAM_ID}, root parent: ${MDFLOW_ROOT_PARENT_ID}"
echo ""
echo "Usage in Claude Code:"
echo "  /yt-summary <youtube-url>"
echo "  /yt-summary-mdflow <youtube-url>"
