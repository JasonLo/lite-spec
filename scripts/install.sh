#!/bin/sh
# lite-spec installer — copies the spec-* skills into a Claude Code skills dir.
#
# One-liner (prompts for location; default: per-project):
#   curl -LsSf https://raw.githubusercontent.com/JasonLo/lite-spec/main/scripts/install.sh | sh
#
# Non-interactive — choose explicitly:
#   curl -LsSf .../install.sh | sh -s -- --project   # ./.claude/skills/
#   curl -LsSf .../install.sh | sh -s -- --global    # ~/.claude/skills/
#
# Re-running this script updates an existing install in place.

set -eu

REPO="JasonLo/lite-spec"
REF="${LITE_SPEC_REF:-main}"
MODE=""

usage() {
    cat <<EOF
lite-spec installer

Usage:
  install.sh [--project | --global] [--ref REF]

Options:
  --project      install into \$PWD/.claude/skills/ (interactive default)
  --global       install into \$HOME/.claude/skills/
  --ref REF      git branch, tag, or commit SHA to install from (default: main)
  -h, --help     show this message

With no flag, the installer prompts you to choose project (default) or global.

Environment:
  LITE_SPEC_REF  same as --ref
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --global)  MODE="global"; shift ;;
        --project) MODE="project"; shift ;;
        --ref)
            [ $# -ge 2 ] || { echo "error: --ref requires a value" >&2; exit 2; }
            REF="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "error: unknown argument: $1" >&2; usage >&2; exit 2 ;;
    esac
done

if [ -z "$MODE" ]; then
    MODE="project"
    # Subshell isolates redirection failure: under dash + `set -e`, a failed
    # `> /dev/tty` aborts the parent script; running it in `( ... )` keeps us alive.
    if ( : > /dev/tty ) 2>/dev/null; then
        printf 'Install lite-spec where?\n  [P]roject  ./.claude/skills/  (default)\n  [G]lobal   ~/.claude/skills/\nChoice [P/g]: ' > /dev/tty
        REPLY=""
        read REPLY < /dev/tty || REPLY=""
        case "$REPLY" in
            g|G|global) MODE="global" ;;
        esac
    fi
fi

case "$MODE" in
    global)  DEST="${HOME}/.claude/skills" ;;
    project) DEST="$(pwd)/.claude/skills" ;;
esac

need() {
    command -v "$1" >/dev/null 2>&1 || {
        echo "error: '$1' is required but not installed" >&2
        exit 1
    }
}
need curl
need tar

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT INT TERM

echo "lite-spec: fetching ${REPO}@${REF}"
# codeload accepts branches, tags, and commit SHAs via the same /tar.gz/<ref> path
if ! curl -fsSL "https://codeload.github.com/${REPO}/tar.gz/${REF}" -o "${TMP}/src.tgz"; then
    echo "error: could not download ${REPO}@${REF}" >&2
    exit 1
fi

tar -xzf "${TMP}/src.tgz" -C "${TMP}"
SRC=""
for d in "${TMP}"/*/skills; do
    [ -d "$d" ] || continue
    SRC="$d"
    break
done
if [ -z "$SRC" ]; then
    echo "error: could not locate skills/ in downloaded tarball" >&2
    exit 1
fi

mkdir -p "$DEST"
INSTALLED=""
for skill in "$SRC"/spec-*; do
    [ -d "$skill" ] || continue
    name="$(basename "$skill")"
    rm -rf "${DEST:?}/${name}"
    cp -R "$skill" "$DEST/"
    INSTALLED="${INSTALLED} ${name}"
done

if [ -z "$INSTALLED" ]; then
    echo "error: no spec-* skills found in ${REPO}@${REF}" >&2
    exit 1
fi

cat <<EOF
lite-spec: installed into ${DEST}
  skills:${INSTALLED}

Next: open a project in Claude Code and run /spec-init to bootstrap it.
Re-run this script to update.
EOF
