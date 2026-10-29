#!/usr/bin/env bash
# install-policies.sh — Generate .claude/rules/policies/ from content policy files
#
# Source of truth: content/personal/projects/emsemioverse/policies/
# Output: .claude/rules/policies/ (Claude Code native rule files)
#
# Policy files are the authoritative source. Rule files are build artifacts.
# Run this script whenever policies change.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RULES_DIR="$REPO_ROOT/.claude/rules/policies"

# Try content as submodule first, then as sibling directory
POLICIES_REL="personal/projects/emsemioverse/policies"
if [ -d "$REPO_ROOT/content/$POLICIES_REL" ]; then
    POLICIES_DIR="$REPO_ROOT/content/$POLICIES_REL"
elif [ -d "$(dirname "$REPO_ROOT")/content/$POLICIES_REL" ]; then
    POLICIES_DIR="$(dirname "$REPO_ROOT")/content/$POLICIES_REL"
else
    echo "ERROR: Policies directory not found."
    echo "Tried: $REPO_ROOT/content/$POLICIES_REL"
    echo "Tried: $(dirname "$REPO_ROOT")/content/$POLICIES_REL"
    echo "Make sure the content submodule is initialized or content is a sibling checkout."
    exit 1
fi

echo "Using policies from: $POLICIES_DIR"

mkdir -p "$RULES_DIR"

# Clean existing generated rules
rm -f "$RULES_DIR"/*.md

count=0
for policy_file in "$POLICIES_DIR"/[0-9]*.md; do
    [ -f "$policy_file" ] || continue

    filename="$(basename "$policy_file")"

    # Extract description from frontmatter
    description="$(sed -n '/^description:/{ s/^description: *"//; s/"$//; p; }' "$policy_file")"

    # Extract operational implications section (everything after "## Operational implications")
    implications="$(sed -n '/^## Operational implications$/,/^## /{ /^## Operational implications$/d; /^## /d; p; }' "$policy_file" | sed '/^$/{ N; /^\n$/d; }')"

    # Build the rule file: description + implications + source pointer
    {
        echo "$description"
        echo ""
        if [ -n "$implications" ]; then
            echo "$implications"
        fi
        echo "Source: content/personal/projects/emsemioverse/policies/$filename"
    } > "$RULES_DIR/$filename"

    count=$((count + 1))
    echo "  installed: $filename"
done

echo ""
echo "Installed $count policy rules to $RULES_DIR/"
