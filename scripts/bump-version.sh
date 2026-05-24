#!/bin/sh
# lite-spec version bumper + release tool.
#
# Usage:
#   scripts/bump-version.sh {major|minor|patch}              # bump + commit + tag + push + gh release
#   scripts/bump-version.sh {major|minor|patch} --bump-only  # only edit the manifests, no git/release
#
# Full mode (default) performs, in order:
#   1. Bumps "version" in .claude-plugin/{plugin,marketplace}.json
#   2. git commit -m "chore: release v<new>"
#   3. git tag v<new>
#   4. git push origin <current-branch> --follow-tags
#   5. gh release create v<new> --generate-notes
#
# Requirements (full mode): clean working tree, gh CLI authenticated.

set -eu

usage() {
    cat <<EOF
usage: $0 {major|minor|patch} [--bump-only]

Bumps the version in:
  .claude-plugin/plugin.json       (top-level "version")
  .claude-plugin/marketplace.json  (plugins[0].version)

Without --bump-only, also commits, tags v<new>, pushes the current branch with
the tag, and creates a GitHub release with --generate-notes. Requires a clean
working tree and an authenticated 'gh' CLI.
EOF
}

BUMP=""
BUMP_ONLY=0
for arg in "$@"; do
    case "$arg" in
        major|minor|patch) BUMP="$arg" ;;
        --bump-only)       BUMP_ONLY=1 ;;
        -h|--help)         usage; exit 0 ;;
        *) echo "error: unknown argument: $arg" >&2; usage >&2; exit 2 ;;
    esac
done

if [ -z "$BUMP" ]; then
    echo "error: must specify major, minor, or patch" >&2
    usage >&2
    exit 2
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PLUGIN=".claude-plugin/plugin.json"
MARKET=".claude-plugin/marketplace.json"

for f in "$PLUGIN" "$MARKET"; do
    [ -f "$f" ] || { echo "error: $f not found" >&2; exit 1; }
done

# Preflight (full-release mode only).
if [ "$BUMP_ONLY" -eq 0 ]; then
    command -v gh >/dev/null 2>&1 || {
        echo "error: gh CLI not installed (https://cli.github.com/)" >&2
        echo "       re-run with --bump-only to skip the release step." >&2
        exit 1
    }
    if [ -n "$(git status --porcelain)" ]; then
        echo "error: working tree not clean — commit or stash before releasing." >&2
        git status --short >&2
        exit 1
    fi
fi

extract_version() {
    sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*\)".*/\1/p' "$1" | head -n1
}

PLUGIN_VER="$(extract_version "$PLUGIN")"
MARKET_VER="$(extract_version "$MARKET")"

[ -n "$PLUGIN_VER" ] || { echo "error: could not parse version from $PLUGIN" >&2; exit 1; }
[ -n "$MARKET_VER" ] || { echo "error: could not parse version from $MARKET" >&2; exit 1; }

if [ "$PLUGIN_VER" != "$MARKET_VER" ]; then
    echo "error: versions out of sync — plugin.json=${PLUGIN_VER}, marketplace.json=${MARKET_VER}" >&2
    echo "       fix the mismatch manually, then re-run." >&2
    exit 1
fi

CURRENT="$PLUGIN_VER"
MAJOR="${CURRENT%%.*}"
REST="${CURRENT#*.}"
MINOR="${REST%%.*}"
PATCH="${REST#*.}"

case "$BUMP" in
    major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0 ;;
    minor) MINOR=$((MINOR + 1)); PATCH=0 ;;
    patch) PATCH=$((PATCH + 1)) ;;
esac

NEW="${MAJOR}.${MINOR}.${PATCH}"
TAG="v${NEW}"

# Tag conflict check before mutating anything.
if [ "$BUMP_ONLY" -eq 0 ] && git rev-parse "${TAG}" >/dev/null 2>&1; then
    echo "error: tag ${TAG} already exists locally — pick a different bump." >&2
    exit 1
fi

# Portable in-place edit: -i.bak + rm works on both GNU and BSD sed.
for f in "$PLUGIN" "$MARKET"; do
    sed -i.bak "s/\"version\"[[:space:]]*:[[:space:]]*\"${CURRENT}\"/\"version\": \"${NEW}\"/" "$f"
    rm -f "${f}.bak"
done

if command -v python3 >/dev/null 2>&1; then
    python3 -c "import json,sys
[json.load(open(f)) for f in sys.argv[1:]]" "$PLUGIN" "$MARKET" || {
        echo "error: post-bump JSON failed to parse — restore via 'git checkout .claude-plugin/'" >&2
        exit 1
    }
fi

echo "bumped ${CURRENT} -> ${NEW}"

if [ "$BUMP_ONLY" -eq 1 ]; then
    cat <<EOF
manifests updated. To finish the release manually:
  git commit -am "chore: release ${TAG}"
  git tag ${TAG}
  git push --follow-tags
  gh release create ${TAG} --generate-notes
EOF
    exit 0
fi

BRANCH="$(git rev-parse --abbrev-ref HEAD)"

echo "→ commit"
git add "$PLUGIN" "$MARKET"
git commit -m "chore: release ${TAG}"

echo "→ tag ${TAG}"
git tag "${TAG}"

echo "→ push origin ${BRANCH} --follow-tags"
git push origin "${BRANCH}" --follow-tags

echo "→ gh release create ${TAG}"
gh release create "${TAG}" --generate-notes --title "${TAG}"

echo "done: released ${TAG}"
