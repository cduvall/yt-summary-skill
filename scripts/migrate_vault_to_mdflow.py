"""Migrate cached Obsidian vault summaries to mdFlow-ready JSON manifest.

CLI:
    python migrate_vault_to_mdflow.py [--limit N] [--channel CHANNEL] [--vault-path PATH]

Outputs a JSON manifest to stdout describing all items to be created in mdFlow.
A Claude agent then reads the manifest and calls mdFlow MCP tools to create the items.
"""

import argparse
import json
import os
import re
import sys
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


def _truncate_title(title: str) -> str:
    """Truncate title to 100 chars at a word boundary."""
    if len(title) <= 100:
        return title
    truncated = title[:100]
    # if we cut mid-word, back off to previous word boundary
    if title[100:101] and truncated[-1] != " ":
        last_space = truncated.rfind(" ")
        if last_space > 0:
            truncated = truncated[:last_space]
    return truncated.rstrip()


def _strip_date(cached_at: str) -> str:
    """Return only the date portion of a cached_at value (ISO or plain date)."""
    if "T" in cached_at:
        return cached_at.split("T")[0]
    return cached_at


def _build_frontmatter(video_id: str, title: str, channel: str, url: str, cached_at: str) -> str:
    """Build YAML frontmatter block for mdFlow note body."""
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


def _build_summary_note_body(parsed: dict, frontmatter: str) -> str:
    """Build the summary note body with ## Heading format sections."""
    title_eval, summary_text, takeaways_text, protocols_text = _parse_summary_sections(
        parsed["summary"]
    )

    parts = [frontmatter]

    if title_eval:
        parts.append(f"\n## Title Evaluation\n\n{title_eval}")
    if summary_text:
        parts.append(f"\n## Summary\n\n{summary_text}")
    if takeaways_text:
        parts.append(f"\n## Top Takeaways\n\n{takeaways_text}")
    if protocols_text:
        parts.append(f"\n## Protocols & Instructions\n\n{protocols_text}")

    return "\n".join(parts)


def _build_transcript_note_body(parsed: dict, frontmatter: str) -> str:
    """Build the transcript note body."""
    transcript = parsed.get("full_text", "")
    if transcript:
        return frontmatter + "\n\n" + transcript
    return frontmatter


def _extract_raw_field(content: str, field: str) -> str:
    """Extract a raw frontmatter field value from markdown content."""
    match = re.search(rf"^{field}:\s*(.+)$", content, re.MULTILINE)
    return match.group(1).strip() if match else ""


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
    results = []
    if not vault_path.is_dir():
        print(f"Error: vault path does not exist: {vault_path}", file=sys.stderr)
        sys.exit(1)

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
        description="Emit a JSON migration manifest for mdFlow import."
    )
    parser.add_argument("--limit", type=int, default=5, help="Max items to emit (default: 5)")
    parser.add_argument("--channel", type=str, default=None, help="Restrict to one channel name")
    parser.add_argument("--vault-path", type=str, default=None, help="Vault root directory")
    args = parser.parse_args()

    vault_path = _load_vault_path(args.vault_path)
    all_files = _walk_vault(vault_path, args.channel)

    items = []
    skipped = []

    for channel, fpath in all_files:
        if len(items) >= args.limit:
            break

        # Skip known non-summary files by name
        if fpath.name in _SKIP_FILENAMES:
            skipped.append({"file": str(fpath), "reason": "excluded filename"})
            continue

        # Read and parse
        try:
            content = fpath.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"Warning: could not read {fpath}: {exc}", file=sys.stderr)
            skipped.append({"file": str(fpath), "reason": f"read error: {exc}"})
            continue

        try:
            parsed = parse_markdown(content)
        except Exception as exc:
            print(f"Warning: parse failed for {fpath}: {exc}", file=sys.stderr)
            skipped.append({"file": str(fpath), "reason": f"parse error: {exc}"})
            continue

        # Skip if no video_id
        if not parsed.get("video_id"):
            skipped.append({"file": str(fpath), "reason": "no video_id"})
            continue

        # Skip if no summary
        if not parsed.get("summary"):
            skipped.append({"file": str(fpath), "reason": "no summary"})
            continue

        video_id = parsed["video_id"]
        title = parsed["title"]

        # url and cached_at are not in ParsedMarkdown; read from raw content
        url = _extract_raw_field(content, "url") or f"https://www.youtube.com/watch?v={video_id}"
        cached_at = _extract_raw_field(content, "cached_at")

        # Build note title with truncation
        truncated_title = _truncate_title(title)
        note_title = f"{truncated_title} [{video_id}]"

        # Build frontmatter block for note bodies
        frontmatter = _build_frontmatter(video_id, title, channel, url, cached_at)

        # Build note bodies
        summary_note_body = _build_summary_note_body(parsed, frontmatter)
        transcript_note_body = _build_transcript_note_body(parsed, frontmatter)

        # Determine has_transcript
        has_transcript = bool(parsed.get("full_text", "").strip())

        items.append(
            {
                "channel": channel,
                "video_id": video_id,
                "url": url,
                "note_title": note_title,
                "summary_note_body": summary_note_body,
                "transcript_title": f"{video_id} Transcript",
                "transcript_note_body": transcript_note_body,
                "has_transcript": has_transcript,
            }
        )

    manifest = {
        "total": len(items),
        "items": items,
        "skipped": skipped,
    }

    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
