#!/bin/sh
# lite-spec installer — copies the ls-* skills into a Claude Code skills dir.
#
# One-liner (default: install globally into ~/.claude/skills/):
#   curl -LsSf https://raw.githubusercontent.com/JasonLo/lite-spec/main/scripts/install.sh | sh
#
# Per-project install (./.claude/skills/):
#   curl -LsSf https://raw.githubusercontent.com/JasonLo/lite-spec/main/scripts/install.sh | sh -s -- --project
#
# Re-running this script updates an existing install in place.

set -eu

REPO="JasonLo/lite-spec"
REF="${LITE_SPEC_REF:-main}"
MODE="global"
PREFIX=""

usage() {
    cat <<EOF
lite-spec installer

Usage:
  install.sh [--global | --project | --prefix DIR] [--ref REF]

Options:
  --global       install into \$HOME/.claude/skills/ (default)
  --project      install into \$PWD/.claude/skills/
  --prefix DIR   install into DIR (each ls-* skill is copied as DIR/ls-*)
  --ref REF      git branch, tag, or commit SHA to install from (default: main)
  -h, --help     show this message

Environment:
  LITE_SPEC_REF  same as --ref
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --global)  MODE="global"; shift ;;
        --project) MODE="project"; shift ;;
        --prefix)
            [ $# -ge 2 ] || { echo "error: --prefix requires a value" >&2; exit 2; }
            MODE="prefix"; PREFIX="$2"; shift 2 ;;
        --ref)
            [ $# -ge 2 ] || { echo "error: --ref requires a value" >&2; exit 2; }
            REF="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "error: unknown argument: $1" >&2; usage >&2; exit 2 ;;
    esac
done

case "$MODE" in
    global)  DEST="${HOME}/.claude/skills" ;;
    project) DEST="$(pwd)/.claude/skills" ;;
    prefix)  DEST="$PREFIX" ;;
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
for skill in "$SRC"/ls-*; do
    [ -d "$skill" ] || continue
    name="$(basename "$skill")"
    rm -rf "${DEST:?}/${name}"
    cp -R "$skill" "$DEST/"
    INSTALLED="${INSTALLED} ${name}"
done

if [ -z "$INSTALLED" ]; then
    echo "error: no ls-* skills found in ${REPO}@${REF}" >&2
    exit 1
fi

cat <<EOF
lite-spec: installed into ${DEST}
  skills:${INSTALLED}

Done! Invoke any skill in Claude Code by name (e.g. /ls-intent) or by describing the task.
Re-run this script to update.
EOF
