Prepare and create a PR by default using @agents/file-ops.md.

## Steps

1. Check for PR template at `.github/pull_request_template.md` - if exists, follow its structure
2. **Calculate AI metrics** using the `ai-metrics` skill:
   ```bash
   .claude/skills/ai-metrics/scripts/ai-metrics.sh develop
   ```
3. Generate concise PR content:
   - **Title**: `<ticket-id>: <short summary>` or descriptive title
   - **Description**: Brief, focused summary of changes (not a wall of text)
   - **AI Contribution section**: Include metrics from step 2
4. Show PR preview to user
5. Create using `gh pr create`
6. Return and display the PR URL

## Description Guidelines

- Lead with a 1-2 sentence summary of what changed and why
- Use bullet points for multiple changes
- Reference ticket numbers if applicable
- Skip obvious details (e.g., "updated imports")
- Include test coverage notes only if notable
- If relevant include a dependencies section for potential blockers

## AI Contribution Section

Include this section in every PR (the HTML comments enable automated parsing by AppFire):

```markdown
## AI Contribution

<!-- AI_METRICS_START -->

| Metric              | Value                           |
| ------------------- | ------------------------------- |
| AI-assisted commits | X of Y (Z%)                     |
| Lines changed (AI)  | +A / -B (C% of total)           |
| Co-author           | Cursor <cursoragent@cursor.com> |

<!-- AI_METRICS_END -->
```

## Example

```
## Summary
Adds input validation to the user registration endpoint to prevent invalid email formats.

## Changes
- Added email regex validation in `user_handler.py`
- Added unit tests for valid/invalid email cases
- Updated error response to include validation details

## Testing
- Unit tests added (5 new tests)

## AI Contribution

<!-- AI_METRICS_START -->
| Metric | Value |
|--------|-------|
| AI-assisted commits | 2 of 3 (67%) |
| Lines changed (AI) | +45 / -12 (85% of total) |
| Co-author | Cursor <cursoragent@cursor.com> |
<!-- AI_METRICS_END -->
```

No confirmation needed - user invoked /pr intentionally.
