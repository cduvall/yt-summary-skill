#!/usr/bin/env python3
"""Migration script to convert JSON cache files to markdown format.

This script:
1. Finds all .json files in the cache directory
2. Converts each to markdown format
3. Deletes the original JSON file
4. Reports migration progress

Safe to run multiple times - skips already-migrated files.
"""

import json
import sys
from pathlib import Path

# Add parent directory to path for imports before other imports
_parent_dir = Path(__file__).parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

from yt_summary.config import get_obsidian_vault_path, load_config  # noqa: E402
from yt_summary.markdown import generate_markdown  # noqa: E402
from yt_summary.metadata import sanitize_filename  # noqa: E402


def migrate_json_to_markdown() -> None:
    """Migrate all JSON cache files to markdown format."""
    # Load configuration
    load_config()

    # Get cache directory
    cache_dir = get_obsidian_vault_path()

    if not cache_dir.exists():
        print(f"Cache directory does not exist: {cache_dir}")
        print("Nothing to migrate.")
        return

    # Find all JSON files
    json_files = list(cache_dir.glob("*.json"))

    if not json_files:
        print("No JSON files found to migrate.")
        return

    print(f"Found {len(json_files)} JSON file(s) to migrate.")
    print(f"Target directory: {cache_dir}")
    print()

    migrated = 0
    errors = 0

    for json_file in json_files:
        try:
            print(f"Migrating: {json_file.name}")

            # Load JSON data
            json_data = json.loads(json_file.read_text())

            # Extract fields
            video_id = json_data.get("video_id", "")
            title = json_data.get("title", "")
            full_text = json_data.get("full_text", "")
            summary = json_data.get("summary", "")

            if not video_id:
                print("  ⚠️  Skipping: missing video_id")
                errors += 1
                continue

            # Generate markdown filename
            if title:
                sanitized_title = sanitize_filename(title)
                md_filename = f"{video_id} – {sanitized_title}.md"
            else:
                md_filename = f"{video_id}.md"

            md_file = cache_dir / md_filename

            # Check if markdown file already exists
            if md_file.exists():
                print(f"  ⚠️  Skipping: {md_filename} already exists")
                # Still delete JSON to clean up
                json_file.unlink()
                continue

            # Generate markdown content
            markdown_content = generate_markdown(video_id, title, full_text, summary)

            # Write markdown file
            md_file.write_text(markdown_content)

            # Delete original JSON file
            json_file.unlink()

            print(f"  ✓ Migrated to: {md_filename}")
            migrated += 1

        except Exception as e:
            print(f"  ✗ Error: {e}")
            errors += 1

    print()
    print("=" * 60)
    print("Migration complete!")
    print(f"Successfully migrated: {migrated} file(s)")
    if errors > 0:
        print(f"Errors encountered: {errors} file(s)")
    print("=" * 60)


if __name__ == "__main__":
    migrate_json_to_markdown()
