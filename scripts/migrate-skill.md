# mdFlow Vault Migration Guide

Step-by-step instructions for migrating cached Obsidian YouTube summaries into mdFlow.
Run these steps in order. Each MCP call is shown with its exact parameters.

---

## Step 1: Generate the Migration Manifest

Run the Python script to produce a JSON manifest of items to create:

```bash
\
  /Users/xian/.claude/skills/yt-summary/venv/bin/python \
  scripts/migrate_vault_to_mdflow.py --limit 5 \
  > /tmp/migration_manifest.json && \
  cat /tmp/migration_manifest.json
```

To migrate a specific channel only:
```bash
... --limit 50 --channel "Alex Hormozi" > /tmp/migration_manifest.json
```

To migrate the full vault (188 items):
```bash
... --limit 500 > /tmp/migration_manifest.json
```

Inspect the output:
- `total`: number of items that will be created
- `items`: array of video summaries with pre-built note bodies
- `skipped`: files that were excluded and why

---

## Step 2: Parse the Manifest

Load and review the manifest. Key fields per item:

| Field | Description |
|---|---|
| `channel` | Channel name (maps to an mdFlow area) |
| `video_id` | YouTube video ID |
| `note_title` | Title for the summary note (e.g. `My Video [abc123]`) |
| `summary_note_body` | Full markdown body: YAML frontmatter + `## Heading` summary sections |
| `transcript_title` | Title for the transcript note (e.g. `abc123 Transcript`) |
| `transcript_note_body` | Full markdown body: YAML frontmatter + transcript text |
| `has_transcript` | `true` if the file had a `## Full Transcript` section |

---

## Step 3: Switch to the YouTube mdFlow Stream

```
mcp__claude_ai_MDFlow_Secure__switch_stream
  stream_id: -YpMGhh
```

---

## Step 4: List Existing Channel Areas

```
mcp__claude_ai_MDFlow_Secure__list_items
  parent: iwdoj9b
  type: area
```

Build a map of `channel_name → id` from the results, excluding items where
`status == "archived"`. You will use this map in Step 5 to determine whether
each channel already exists.

---

## Step 5: Create Items by Channel

Process all unique channels in the manifest. For each channel, call
`bulk_create_items` once with all that channel's notes in a single call.

> **Note:** Skip the `children` array entirely for items where `has_transcript` is `false`.

### Case A: Channel area already exists in mdFlow

Call `bulk_create_items` with the summary notes as top-level items, each
parented to the existing channel area:

```
mcp__claude_ai_MDFlow_Secure__bulk_create_items
  items: [
    {
      "parent": "<existing_channel_area_id>",
      "title": "<item.note_title>",
      "type": "note",
      "status": "living",
      "tags": ["youtube", "summary"],
      "body": "<item.summary_note_body>",
      "children": [
        {
          "title": "<item.transcript_title>",
          "type": "note",
          "status": "living",
          "tags": ["youtube", "transcript"],
          "body": "<item.transcript_note_body>"
        }
      ]
    },
    ... (all notes for this channel)
  ]
```

### Case B: Channel area does NOT exist in mdFlow

Call `bulk_create_items` with a single top-level area item containing all
the channel's summary notes as children, and each transcript as a grandchild:

```
mcp__claude_ai_MDFlow_Secure__bulk_create_items
  items: [
    {
      "parent": "iwdoj9b",
      "title": "<channel_name>",
      "type": "area",
      "status": "living",
      "children": [
        {
          "title": "<item.note_title>",
          "type": "note",
          "status": "living",
          "tags": ["youtube", "summary"],
          "body": "<item.summary_note_body>",
          "children": [
            {
              "title": "<item.transcript_title>",
              "type": "note",
              "status": "living",
              "tags": ["youtube", "transcript"],
              "body": "<item.transcript_note_body>"
            }
          ]
        },
        ... (all notes for this channel)
      ]
    }
  ]
```

---

## Step 6: Verify and Report

After all `bulk_create_items` calls complete:

1. Note the total wall-clock time for each call (log start/end time per channel batch).
2. Confirm the returned flat item list matches the expected count.
3. Spot-check one or two notes: call `mcp__claude_ai_MDFlow_Secure__get_item` on a
   returned note ID and verify `body`, `tags`, and `status` look correct.

---

## Reference: Script Options

```
python scripts/migrate_vault_to_mdflow.py
  [--limit N]          Max items to emit (default: 5)
  [--channel CHANNEL]  Restrict to one channel name
  [--vault-path PATH]  Vault root (default: OBSIDIAN_VAULT_PATH env var or ./Summaries)
```

## Reference: Key mdFlow IDs

| Name | ID |
|---|---|
| YouTube stream | `-YpMGhh` |
| Root parent area (Summaries) | `iwdoj9b` |
