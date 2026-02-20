Upgrade framework files to the latest version while preserving project-specific configuration.

## Overview

This command helps you update the AI SDLC framework components (agents, commands, hooks, skills, workflow rules) to the latest version without affecting your project-specific files.

## How It Works

The upgrade **dynamically discovers** all files in the latest template and compares them against your local `.cursor/` directory. Files matching `PRESERVE_PATTERNS` are skipped; everything else is eligible for upgrade.

This means new framework files (agents, skills, commands) are automatically picked up without needing to maintain a hardcoded list.

## File Categories

| Category                         | Examples                                                                                                              | Behavior                                       |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| **Framework** (upgradeable)      | `agents/*.md`, `commands/*.md`, `hooks/*`, `skills/**`, `hooks.json`, `mcp.json`, `rules/workflow.mdc`, `README.md`   | Compare and offer to update                    |
| **Project-specific** (preserved) | `rules/workspace.mdc`, `rules/jira-conventions.mdc`, `rules/_project-*.mdc`, `plans/*`, `scratchpad.md`, `*/.gitkeep` | Never touched                                  |
| **User-created** (invisible)     | Any file you added that doesn't exist in the template (e.g. `agents/my-agent.md`, `skills/my-skill/`)                 | Not seen by upgrade, never modified or deleted |

## Important: What the Upgrade Does NOT Do

- **Never deletes files** -- If a framework file is removed or renamed in the template, your local copy stays. The upgrade detects these as orphans and warns the user so they can decide whether to remove them.
- **Never touches user-created files** -- Files that exist only in your project (not in the template) are completely invisible to the upgrade.
- **Never overwrites preserved files** -- Even if the template version of a preserved file changes, your local version is kept as-is.
- **Never auto-applies** -- In interactive mode, every change requires your approval. In `--auto` mode (CLI only), all framework updates are applied but preserved files are still respected.
- **Detects orphaned files** -- Files in framework directories (agents/, commands/, hooks/, rules/, skills/) that exist locally but not in the current template are flagged with a warning. This catches deprecated files that could still affect your workflow.

## Your Task

### Step 1: Fetch Latest Framework

Clone the framework repository to a temporary location:

```bash
TEMP_DIR=$(mktemp -d)
git clone --depth 1 git@github.com:tcardoso-95/ai-sdlc-framework.git "$TEMP_DIR"
```

If the user provides a local path, use that instead of cloning.

### Step 2: Compare Framework Files

Dynamically discover all files in `$TEMP_DIR/template/.cursor/` and compare against the local `.cursor/` directory.

**Skip files matching these preserve patterns:**

- `rules/workspace.mdc` -- User's project configuration
- `rules/jira-conventions.mdc` -- User's Jira customizations
- `rules/_project-*.mdc` -- Project-specific rules
- `plans/*` -- User's implementation plans
- `scratchpad.md` -- User's working memory
- `*/.gitkeep` -- Placeholder files

For each remaining file:

1. Check if it exists locally
2. If not, it's a NEW file -- ask user if they want to add it
3. If it exists, compare contents
4. If different, show the user what changed

### Step 3: Present Changes

For each file with differences, explain:

1. **What changed** -- Summarize the key differences (new sections, modified behavior, bug fixes)
2. **Impact** -- How this might affect their workflow
3. **Recommendation** -- Whether they should apply this update

Use the AskQuestion tool to let the user decide for each changed file:

- Apply the update (replace local with latest)
- Skip this file (keep local version)
- View the full diff first

### Step 4: Apply Updates

For files the user approved:

1. Back up the original (optional, mention they can use git to revert)
2. Copy the new version from the temp directory
3. Report success

### Step 5: Cleanup and Summary

1. Remove the temporary directory
2. Report what was updated, skipped, and preserved

Example summary:

```
Upgrade Complete

Applied updates:
- agents/reviewer.md - Added Pre-Approval Checklist
- skills/ai-metrics/SKILL.md - Updated output format
- commands/init.md - Added Version Drift Detection

Skipped (your choice):
- agents/plan-evaluator.md

⚠️  Orphaned files (no longer in template):
- agents/old-deprecated-agent.md
  (May have been removed or renamed upstream. Review and delete if no longer needed.)

Preserved (project-specific):
- rules/workspace.mdc
- rules/jira-conventions.mdc
- rules/_project-*.mdc
- plans/
- scratchpad.md

Not modified (user-created, not in template):
- agents/my-custom-agent.md
- skills/my-custom-skill/
```

## Edge Cases to Communicate

When presenting the upgrade summary, proactively inform the user about these situations if they apply:

| Situation                                        | What to Tell the User                                                                                                                     |
| ------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------- |
| File exists locally but not in template          | "This file is no longer part of the framework template. It was likely removed or renamed. Review whether you still need it."              |
| A new file has a similar name to an existing one | "This might be a renamed version of [old file]. Review both and remove the old one if it's been superseded."                              |
| User modified a framework file                   | "You've customized this framework file. The upgrade will overwrite your changes. Review the diff carefully or skip to keep your version." |
| Template adds a new directory                    | "New framework directory detected. This contains [description]. Recommended to add."                                                      |

## Important Notes

- **Never modify project-specific files** -- These contain configuration unique to this project
- **Git is your safety net** -- All changes can be reverted with `git checkout .cursor/`
- **Review before applying** -- If you've customized framework files, review diffs carefully
- **CLI alternative** -- For quick upgrades, users can run `cursor-upgrade` from the terminal
- **User files are safe** -- Any agents, commands, skills, or rules you created yourself are never touched by the upgrade
