"""Convert Obsidian vault markdown files into the mdFlow import directory format.

Produces a directory tree that can be bulk-imported into mdFlow without
MCP API calls:

    {output}/
    ├── README.md                          ← area frontmatter (root)
    └── {channel-slug}/
        ├── README.md                      ← area frontmatter (channel)
        └── {note-slug}/
            ├── README.md                  ← summary note frontmatter + body
            └── {video_id_lower}-transcript.md  ← transcript frontmatter + body

CLI:
    python convert_vault_to_mdflow_import.py \\
      [--vault-path PATH]   # default: OBSIDIAN_VAULT_PATH env or ./Summaries
      [--output PATH]       # default: ./tmp/mdflow_import
      [--limit N]           # max videos to convert (for testing)
      [--channel NAME]      # restrict to one channel
"""

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# Allow running from repo root or scripts/
_repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(_repo_root))

import yt_summary.markdown as _md_module  # noqa: E402
from yt_summary.markdown import parse_markdown  # noqa: E402

_parse_summary_sections = _md_module._parse_summary_sections

# Files to skip by name regardless of location
_SKIP_FILENAMES = {"Daily Review.md", "Starred.md"}


def _slugify(text: str) -> str:
    """Convert text to a URL-safe slug, max 60 chars.

    - Lowercase all
    - Replace non-alphanumeric chars with hyphens
    - Collapse multiple hyphens to one
    - Strip leading/trailing hyphens
    - Truncate at 60 chars, then strip trailing hyphens
    """
    s = text.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s)
    s = s.strip("-")
    s = s[:60]
    s = s.strip("-")
    return s


def _truncate_title(title: str) -> str:
    """Truncate title to 100 chars at a word boundary."""
    if len(title) <= 100:
        return title
    truncated = title[:100]
    if title[100:101] and truncated[-1] != " ":
        last_space = truncated.rfind(" ")
        if last_space > 0:
            truncated = truncated[:last_space]
    return truncated.rstrip()


def _raw_field(text: str, field: str) -> str:
    """Extract a raw frontmatter field value from markdown text."""
    m = re.search(rf"^{field}:\s*(.+)$", text, re.MULTILINE)
    return m.group(1).strip().strip('"') if m else ""


def _strip_date(cached_at: str) -> str:
    """Return only the YYYY-MM-DD portion of a cached_at value."""
    if "T" in cached_at:
        return cached_at.split("T")[0]
    return cached_at


def _mdflow_timestamp(date_str: str) -> str:
    """Convert a YYYY-MM-DD date to an mdFlow ISO timestamp string."""
    return f'"{date_str}T00:00:00.000Z"'


def _area_readme(title: str, ts: str) -> str:
    """Build a README.md for an area (root or channel)."""
    return (
        f'---\ntitle: "{title}"\ntype: area\nstatus: living\n'
        f"created: {ts}\nmodified: {ts}\n---\n"
    )


def _note_readme(note_title: str, ts: str, body: str) -> str:
    """Build a README.md for a summary note."""
    return (
        f'---\ntitle: "{note_title}"\ntype: note\nstatus: living\n'
        f"tags: [youtube, summary]\ncreated: {ts}\nmodified: {ts}\n---\n"
        f"\n{body}\n"
    )


def _transcript_readme(transcript_title: str, ts: str, body: str) -> str:
    """Build a transcript .md file."""
    return (
        f'---\ntitle: "{transcript_title}"\ntype: note\nstatus: living\n'
        f"tags: [youtube, transcript]\ncreated: {ts}\nmodified: {ts}\n---\n"
        f"\n{body}\n"
    )


def _build_inner_frontmatter(
    video_id: str, title: str, channel: str, url: str, cached_at: str
) -> str:
    """Build the inner YAML frontmatter block that appears in the note body."""
    date = _strip_date(cached_at)
    lines = [
        "---",
        f"video_id: {video_id}",
        f"title: {title}",
        f"channel: {channel}",
        f"url: {url}",
        f"cached_at: {date}",
        "---",
    ]
    return "\n".join(lines)


def _build_summary_body(parsed: dict, inner_fm: str) -> str:
    """Build the summary note body with ## Heading format sections."""
    title_eval, summary_text, takeaways_text, protocols_text = _parse_summary_sections(
        parsed["summary"]
    )

    parts = [inner_fm]

    if title_eval:
        parts.append(f"\n## Title Evaluation\n\n{title_eval}")
    if summary_text:
        parts.append(f"\n## Summary\n\n{summary_text}")
    if takeaways_text:
        parts.append(f"\n## Top Takeaways\n\n{takeaways_text}")
    if protocols_text:
        parts.append(f"\n## Protocols & Instructions\n\n{protocols_text}")

    return "\n".join(parts)


def _build_transcript_body(parsed: dict, inner_fm: str) -> str:
    """Build the transcript note body."""
    transcript = parsed.get("full_text", "")
    if transcript:
        return inner_fm + "\n\n" + transcript
    return inner_fm


def _load_vault_path(vault_path_arg: str | None) -> Path:
    """Resolve vault path from arg, env, or default."""
    if vault_path_arg:
        return Path(vault_path_arg).expanduser().resolve()

    load_dotenv(_repo_root / ".env")
    env_val = os.getenv("OBSIDIAN_VAULT_PATH")
    if env_val:
        return Path(env_val).expanduser().resolve()

    return Path("./Summaries").resolve()


def _walk_vault(vault_path: Path, channel_filter: str | None) -> list[tuple[str, Path]]:
    """Walk vault returning (channel_name, file_path) pairs in sorted order."""
    if not vault_path.is_dir():
        print(f"Error: vault path does not exist: {vault_path}", file=sys.stderr)
        sys.exit(1)

    results = []
    for channel in sorted(os.listdir(vault_path)):
        if channel_filter and channel != channel_filter:
            continue
        channel_path = vault_path / channel
        if not channel_path.is_dir():
            continue
        for fname in sorted(os.listdir(channel_path)):
            if not fname.endswith(".md"):
                continue
            results.append((channel, channel_path / fname))

    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert Obsidian vault to mdFlow import directory format."
    )
    parser.add_argument("--vault-path", type=str, default=None, help="Vault root directory")
    parser.add_argument(
        "--output", type=str, default="./tmp/mdflow_import", help="Output directory"
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Max videos to convert (for testing)"
    )
    parser.add_argument("--channel", type=str, default=None, help="Restrict to one channel name")
    args = parser.parse_args()

    vault_path = _load_vault_path(args.vault_path)
    output_path = Path(args.output).expanduser().resolve()

    all_files = _walk_vault(vault_path, args.channel)

    # Current datetime for root README
    now_ts = f'"{datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")}"'

    # Write root README.md
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "README.md").write_text(_area_readme("Summaries", now_ts), encoding="utf-8")

    converted = 0
    skipped = 0
    channels_seen: set[str] = set()

    for channel, fpath in all_files:
        if args.limit is not None and converted >= args.limit:
            break

        # Skip known non-summary files
        if fpath.name in _SKIP_FILENAMES:
            print(f"Skip (excluded filename): {fpath}", file=sys.stderr)
            skipped += 1
            continue

        # Read file
        try:
            content = fpath.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"Skip (read error): {fpath}: {exc}", file=sys.stderr)
            skipped += 1
            continue

        # Parse
        try:
            parsed = parse_markdown(content)
        except Exception as exc:
            print(f"Skip (parse error): {fpath}: {exc}", file=sys.stderr)
            skipped += 1
            continue

        # Validate required fields
        if not parsed.get("video_id"):
            print(f"Skip (no video_id): {fpath}", file=sys.stderr)
            skipped += 1
            continue

        if not parsed.get("summary"):
            print(f"Skip (no summary): {fpath}", file=sys.stderr)
            skipped += 1
            continue

        video_id = parsed["video_id"]
        title = parsed["title"]
        channel_name = parsed.get("channel") or channel

        # url and cached_at are not in ParsedMarkdown; read from raw content
        url = _raw_field(content, "url") or f"https://www.youtube.com/watch?v={video_id}"
        cached_at = _raw_field(content, "cached_at")
        date_str = _strip_date(cached_at) if cached_at else ""

        # mdFlow timestamps based on cached_at date
        note_ts = _mdflow_timestamp(date_str) if date_str else now_ts

        # Build note title: truncate to 100 chars at word boundary, then add [video_id]
        truncated_title = _truncate_title(title)
        note_title = f"{truncated_title} [{video_id}]"

        # Slugify channel and note
        channel_slug = _slugify(channel_name)
        note_slug = _slugify(note_title)
        transcript_slug = f"{video_id.lower()}-transcript"

        # Ensure channel directory and README exist
        channel_dir = output_path / channel_slug
        if channel_slug not in channels_seen:
            channel_dir.mkdir(parents=True, exist_ok=True)
            (channel_dir / "README.md").write_text(
                _area_readme(channel_name, note_ts), encoding="utf-8"
            )
            channels_seen.add(channel_slug)

        # Create note subdirectory
        note_dir = channel_dir / note_slug
        note_dir.mkdir(parents=True, exist_ok=True)

        # Build inner frontmatter block (appears in note bodies)
        inner_fm = _build_inner_frontmatter(video_id, title, channel_name, url, cached_at)

        # Write summary note README.md
        summary_body = _build_summary_body(parsed, inner_fm)
        (note_dir / "README.md").write_text(
            _note_readme(note_title, note_ts, summary_body), encoding="utf-8"
        )

        # Write transcript file
        transcript_title = f"{video_id} Transcript"
        transcript_body = _build_transcript_body(parsed, inner_fm)
        (note_dir / f"{transcript_slug}.md").write_text(
            _transcript_readme(transcript_title, note_ts, transcript_body), encoding="utf-8"
        )

        converted += 1

    channels_count = len(channels_seen)
    print(f"Converted {converted} videos across {channels_count} channels. Output: {output_path}")


if __name__ == "__main__":
    main()
