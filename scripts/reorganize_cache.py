#!/usr/bin/env python3
"""Reorganization script to move cache files into channel subdirectories with new naming.

This script:
1. Finds all markdown files in the vault (flat structure)
2. For each file:
   - Parses to extract video_id, title, and channel
   - If no channel in frontmatter, fetches it from YouTube
   - Creates channel subdirectory
   - Renames file to new format: {title} [{video_id}].md
   - Moves to channel subdirectory
3. Reports progress and summary

Safe to run multiple times - skips already-reorganized files.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports before other imports
_parent_dir = Path(__file__).parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

from yt_summary.config import get_obsidian_vault_path, load_config  # noqa: E402
from yt_summary.markdown import generate_markdown, parse_markdown  # noqa: E402
from yt_summary.metadata import MetadataError, fetch_video_metadata, sanitize_filename  # noqa: E402


def reorganize_cache() -> None:
    """Reorganize all flat cache files into channel subdirectories."""
    # Load configuration
    load_config()

    # Get vault directory
    vault_dir = get_obsidian_vault_path()

    if not vault_dir.exists():
        print(f"Vault directory does not exist: {vault_dir}")
        print("Nothing to reorganize.")
        return

    # Find all markdown files in the root of the vault (flat structure)
    flat_files = list(vault_dir.glob("*.md"))

    if not flat_files:
        print("No flat markdown files found to reorganize.")
        return

    print(f"Found {len(flat_files)} file(s) in flat structure.")
    print(f"Target directory: {vault_dir}")
    print()

    reorganized = 0
    skipped = 0
    errors = 0

    for md_file in flat_files:
        try:
            print(f"Processing: {md_file.name}")

            # Parse markdown to extract metadata
            try:
                data = parse_markdown(md_file.read_text())
            except Exception as e:
                print(f"  ⚠️  Skipping: cannot parse markdown - {e}")
                errors += 1
                continue

            video_id = data.get("video_id", "")
            title = data.get("title", "")
            channel = data.get("channel", "")
            full_text = data.get("full_text", "")
            summary = data.get("summary", "")

            if not video_id:
                print("  ⚠️  Skipping: missing video_id")
                errors += 1
                continue

            # Fetch channel from YouTube if not in frontmatter
            if not channel:
                print("  → Fetching channel information from YouTube...")
                try:
                    metadata = fetch_video_metadata(video_id)
                    channel = metadata["channel"]
                    if not title:
                        title = metadata["title"]
                    print(f"  → Found channel: {channel or 'Unknown'}")
                except MetadataError as e:
                    print(f"  ⚠️  Could not fetch channel: {e.message}")
                    print("  → Using 'Unknown Channel'")
                    channel = "Unknown Channel"

            # Determine target directory
            if channel:
                channel_dir = vault_dir / sanitize_filename(channel)
                channel_dir.mkdir(exist_ok=True, parents=True)
            else:
                channel_dir = vault_dir
                print("  ⚠️  No channel available, keeping in root")

            # Determine new filename: {title} [{video_id}].md
            if title:
                new_filename = f"{sanitize_filename(title)} [{video_id}].md"
            else:
                new_filename = f"[{video_id}].md"

            new_file = channel_dir / new_filename

            # Check if already reorganized (file exists in target location)
            if new_file.exists() and new_file != md_file:
                print(f"  ⚠️  Skipping: {new_filename} already exists in {channel_dir.name}")
                skipped += 1
                continue

            # Skip if file is already in the correct location
            if new_file == md_file:
                print("  ✓ Already in correct location")
                skipped += 1
                continue

            # Generate new markdown with channel in frontmatter
            markdown_content = generate_markdown(video_id, title, full_text, summary, channel)

            # Write to new location
            new_file.write_text(markdown_content)

            # Delete old file
            md_file.unlink()

            print(f"  ✓ Reorganized to: {channel_dir.name}/{new_filename}")
            reorganized += 1

        except Exception as e:
            print(f"  ✗ Error: {e}")
            errors += 1

    print()
    print("=" * 60)
    print("Reorganization complete!")
    print(f"Successfully reorganized: {reorganized} file(s)")
    if skipped > 0:
        print(f"Skipped (already organized): {skipped} file(s)")
    if errors > 0:
        print(f"Errors encountered: {errors} file(s)")
    print("=" * 60)


if __name__ == "__main__":
    reorganize_cache()
