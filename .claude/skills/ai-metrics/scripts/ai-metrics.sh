#!/bin/bash
# Calculate AI contribution metrics for commits since base branch
#
# Usage: ai-metrics.sh [base_branch]
# Output: Key=value pairs for parsing
#
# Detects commits with "Co-authored-by: Cursor" trailer and calculates
# contribution metrics for PR descriptions.

set -euo pipefail

BASE_BRANCH="${1:-develop}"

# Ensure we're in a git repository
if ! git rev-parse --is-inside-work-tree &>/dev/null; then
    echo "Error: Not inside a git repository" >&2
    exit 1
fi

# Check if base branch exists
if ! git rev-parse --verify "$BASE_BRANCH" &>/dev/null; then
    # Try origin/base_branch
    if ! git rev-parse --verify "origin/$BASE_BRANCH" &>/dev/null; then
        echo "Error: Base branch '$BASE_BRANCH' not found" >&2
        exit 1
    fi
    BASE_BRANCH="origin/$BASE_BRANCH"
fi

# Get merge base to find where current branch diverged
MERGE_BASE=$(git merge-base "$BASE_BRANCH" HEAD 2>/dev/null || echo "")
if [ -z "$MERGE_BASE" ]; then
    echo "Error: Cannot find merge base with '$BASE_BRANCH'" >&2
    exit 1
fi

# Get commits since diverging from base
COMMITS=$(git log --format="%H" "${MERGE_BASE}..HEAD" 2>/dev/null || echo "")

# Initialize counters
total_commits=0
ai_commits=0
total_insertions=0
total_deletions=0
ai_insertions=0
ai_deletions=0

# Process each commit
for commit in $COMMITS; do
    total_commits=$((total_commits + 1))
    
    # Get commit message body (includes trailers)
    commit_body=$(git log -1 --format="%b" "$commit")
    
    # Get diff stats for this commit (handle binary files with -)
    stats=$(git show --numstat --format="" "$commit" 2>/dev/null | awk '
        $1 != "-" && $2 != "-" { ins += $1; del += $2 }
        END { printf "%d %d", ins+0, del+0 }
    ')
    ins=$(echo "$stats" | cut -d' ' -f1)
    del=$(echo "$stats" | cut -d' ' -f2)
    
    total_insertions=$((total_insertions + ins))
    total_deletions=$((total_deletions + del))
    
    # Check for Cursor co-author trailer (case-insensitive)
    if echo "$commit_body" | grep -qi "Co-authored-by:.*cursor"; then
        ai_commits=$((ai_commits + 1))
        ai_insertions=$((ai_insertions + ins))
        ai_deletions=$((ai_deletions + del))
    fi
done

# Calculate totals and percentages
total_changes=$((total_insertions + total_deletions))
ai_changes=$((ai_insertions + ai_deletions))

ai_commit_percentage=0
ai_lines_percentage=0

if [ $total_commits -gt 0 ]; then
    ai_commit_percentage=$((ai_commits * 100 / total_commits))
fi

if [ $total_changes -gt 0 ]; then
    ai_lines_percentage=$((ai_changes * 100 / total_changes))
fi

# Output in parseable format
echo "AI_COMMITS=$ai_commits"
echo "TOTAL_COMMITS=$total_commits"
echo "AI_COMMIT_PERCENTAGE=$ai_commit_percentage"
echo "AI_INSERTIONS=$ai_insertions"
echo "AI_DELETIONS=$ai_deletions"
echo "AI_LINES_CHANGED=$ai_changes"
echo "TOTAL_INSERTIONS=$total_insertions"
echo "TOTAL_DELETIONS=$total_deletions"
echo "TOTAL_LINES_CHANGED=$total_changes"
echo "AI_LINES_PERCENTAGE=$ai_lines_percentage"
