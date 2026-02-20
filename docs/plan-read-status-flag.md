# Plan: Replace `status` with `read` in Markdown Frontmatter

## Objective

Replace the `status: inbox` frontmatter field with a boolean `read: false` field. The Obsidian DataView query filters on `read != true` instead of `status = "inbox"`.

## Files to Change

### 1. `yt_summary/markdown.py`

**`generate_markdown`** (line 38):
- Remove: `"status: inbox"`
- Add: `"read: false"`

**`parse_markdown`** (lines 86, 109–110):
- Remove: `status = _extract_frontmatter_field(frontmatter, "status")`
- Add: `read_raw = _extract_frontmatter_field(frontmatter, "read")`
- Change return dict: remove `"status": status or "inbox"`, add `"read": read_raw.lower() == "true" if read_raw else False`

### 2. `cache/Daily Review.md`

Update DataView query:
- Remove: `WHERE status = "inbox"`
- Add: `WHERE read != true`

### 3. Existing cached `.md` files

All files under `cache/Summaries/` that contain `status: inbox` in frontmatter:
- Replace `status: inbox` with `read: false`

Currently known: `cache/Summaries/Rick Astley/Rick Astley - Never Gonna Give You Up (Official Video) (4K Remaster) [dQw4w9WgXcQ].md`

Use a glob + replace approach in case there are more files.

### 4. `tests/test_markdown.py`

- `test_generate_markdown_basic` (line 38): change `assert "status: inbox" in result` → `assert "read: false" in result`
- `test_parse_markdown_basic` (line 187): change `assert result["status"] == "inbox"` → `assert result["read"] == False`
- `test_roundtrip_basic` (line 542): change `assert parsed_data["status"] == "inbox"` → `assert parsed_data["read"] == False`

## Notes

- No other files reference `status` in frontmatter context (cache.py reads the parsed dict but only uses `video_id`, `title`, `channel`, `full_text`, `summary`).
- `_extract_frontmatter_field` handles unquoted booleans fine since it returns strings; the caller converts to bool.
