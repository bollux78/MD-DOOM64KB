#!/usr/bin/env fish
# One-time GitHub repository branch cleanup.
# Keep ONLY "fullscreen" and "hud" in bollux78/MD-DOOM64KB.
# This script uses gh (GitHub CLI) because the in-chat GitHub connector
# can create/close PRs/branches but cannot change default branch or delete refs.
#
# Use: fish scripts/lab/prune_other_remote_branches.fish --apply
#
# Explicit --apply is required. Runs safety checks before changing anything.
set -l repo bollux78/MD-DOOM64KB
if test (count $argv) -ne 1; or test "$argv[1]" != --apply
    echo "DRY RUN / SAFETY: This one-time operation keeps ONLY the two branches:"
    echo "  fullscreen (R6 SRAM ASM 8.86 FPS)"
    echo "  hud (HUD24 textual 9.39 FPS)"
    echo "To make the changes, run:"
    echo "  fish scripts/lab/prune_other_remote_branches.fish --apply"
    exit 0
end
if not command -sq gh
    echo "ERROR: GitHub CLI 'gh' not installed. On CachyOS: sudo pacman -S github-cli"
    exit 1
end
gh auth status --hostname github.com >/dev/null 2>&1
if test $status -ne 0
    echo "ERROR: gh is not authenticated. Run: gh auth login"
    exit 1
end

set -l repo_full (gh api "repos/$repo" --jq '.full_name'); or exit 1
if test "$repo_full" != "$repo"
    echo "ERROR: wrong GitHub repository ($repo_full)"
    exit 1
end
for keep in fullscreen hud
    set -l head (gh api "repos/$repo/branches/$keep" --jq '.commit.sha')
    if test $status -ne 0; or test -z "$head"
        echo "ABORT: canonical $keep branch is missing"
        exit 1
    end
    echo "KEEP $keep $head"
end

set -l branches (gh api --paginate "repos/$repo/branches?per_page=100" --jq '.[].name')
if test $status -ne 0
    echo "ERROR: unable to list all branches"
    exit 1
end
set -l doomed
for name in $branches
    if test "$name" != fullscreen; and test "$name" != hud
        set -a doomed "$name"
    end
end
echo "Total noncanonical branches: "(count $doomed)
for name in $doomed
    echo "  DELETE $name"
end

# The default branch cannot be deleted. This PATCH requires admin rights.
set -l default (gh api "repos/$repo" --jq '.default_branch'); or exit 1
if test "$default" != fullscreen
    echo "Setting GitHub default branch to 'fullscreen' (was '$default')"
    gh api -X PATCH "repos/$repo" -f default_branch=fullscreen --silent
    if test $status -ne 0
        echo "ERROR: unable to change default branch; nothing was deleted"
        exit 1
    end
end
set -l changed (gh api "repos/$repo" --jq '.default_branch'); or exit 1
if test "$changed" != fullscreen
    echo "ERROR: default branch was not updated. Aborting deletions."
    exit 1
end

set -l failures
for name in $doomed
    echo "DELETE $name"
    gh api -X DELETE "repos/$repo/git/refs/heads/$name" --silent
    if test $status -ne 0
        echo "  FAILED to delete $name"
        set -a failures "$name"
    end
end

set -l remaining (gh api --paginate "repos/$repo/branches?per_page=100" --jq '.[].name'); or exit 1
echo ""
echo "GitHub branches now:"
printf '  %s\n' $remaining
if test (count $remaining) -eq 2; and contains fullscreen $remaining; and contains hud $remaining; and test (count $failures) -eq 0
    echo "SUCCESS: only fullscreen and hud remain. Default: fullscreen."
else
    echo "PARTIAL CLEANUP: inspect failed refs and branch protection."
    exit 1
end
