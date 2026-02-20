---
name: ai-metrics
description: Calculate AI contribution metrics for git commits. Detects Cursor co-authorship and computes statistics. Use when creating PRs, generating commit summaries, or when the user asks about AI contribution percentages.
---

# AI Contribution Metrics

Calculate and format AI contribution metrics for PRs and commit summaries by analyzing git history for Cursor co-authored commits.

## When to Use

- Creating pull requests (`/pr` command)
- Generating commit summaries
- When user asks about AI contribution percentages
- Jira orchestrator auto-mode PR creation

## Quick Start

Run the metrics script to get contribution data:

```bash
.cursor/skills/ai-metrics/scripts/ai-metrics.sh [base_branch]
```

Default base branch is `develop`. The script outputs key=value pairs:

```
AI_COMMITS=3
TOTAL_COMMITS=4
AI_COMMIT_PERCENTAGE=75
AI_INSERTIONS=165
AI_DELETIONS=142
AI_LINES_CHANGED=307
TOTAL_INSERTIONS=165
TOTAL_DELETIONS=142
TOTAL_LINES_CHANGED=307
AI_LINES_PERCENTAGE=100
```

## Output Formatting

### For PR Descriptions

Include this section in PR body (the HTML comments enable automated parsing by AppFire):

```markdown
## AI Contribution

<!-- AI_METRICS_START -->

| Metric              | Value                                                                |
| ------------------- | -------------------------------------------------------------------- |
| AI-assisted commits | {AI_COMMITS} of {TOTAL_COMMITS} ({AI_COMMIT_PERCENTAGE}%)            |
| Lines changed (AI)  | +{AI_INSERTIONS} / -{AI_DELETIONS} ({AI_LINES_PERCENTAGE}% of total) |
| Co-author           | Cursor <cursoragent@cursor.com>                                      |

<!-- AI_METRICS_END -->
```

### For Compact Display

```markdown
**AI Contribution**: {AI_COMMITS}/{TOTAL_COMMITS} commits ({AI_LINES_PERCENTAGE}% of changes)
```

## How It Works

1. Finds the merge base between current branch and base branch
2. Iterates through commits since divergence
3. Detects `Co-authored-by: Cursor` trailer in commit messages
4. Calculates diff stats (insertions/deletions) for each commit
5. Aggregates totals and computes percentages

## Detection Method

Cursor automatically adds this trailer to agent-assisted commits:

```
Co-authored-by: Cursor <cursoragent@cursor.com>
```

The script searches for this pattern (case-insensitive) in commit message bodies.

## Edge Cases

- **No commits**: Returns all zeros
- **No AI commits**: AI percentages will be 0
- **Binary files**: Excluded from line counts
- **Base branch not found**: Script exits with error message
