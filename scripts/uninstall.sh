#!/bin/sh
# lite-spec uninstaller — removes the ls-* skills from a Claude Code skills dir.
#
#   curl -LsSf https://raw.githubusercontent.com/JasonLo/lite-spec/main/scripts/uninstall.sh | sh
#   curl -LsSf https://raw.githubusercontent.com/JasonLo/lite-spec/main/scripts/uninstall.sh | sh -s -- --project

set -eu

MODE="global"
PREFIX=""

usage() {
    cat <<EOF
lite-spec uninstaller

Usage:
  uninstall.sh [--global | --project | --prefix DIR]

Options:
  --global       remove from \$HOME/.claude/skills/ (default)
  --project      remove from \$PWD/.claude/skills/
  --prefix DIR   remove ls-* subdirectories from DIR
  -h, --help     show this message
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --global)  MODE="global"; shift ;;
        --project) MODE="project"; shift ;;
        --prefix)
            [ $# -ge 2 ] || { echo "error: --prefix requires a value" >&2; exit 2; }
            MODE="prefix"; PREFIX="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "error: unknown argument: $1" >&2; usage >&2; exit 2 ;;
    esac
done

case "$MODE" in
    global)  DEST="${HOME}/.claude/skills" ;;
    project) DEST="$(pwd)/.claude/skills" ;;
    prefix)  DEST="$PREFIX" ;;
esac

REMOVED=""
for skill in "$DEST"/ls-*; do
    [ -d "$skill" ] || continue
    name="$(basename "$skill")"
    rm -rf "$skill"
    REMOVED="${REMOVED} ${name}"
done

if [ -z "$REMOVED" ]; then
    echo "lite-spec: no ls-* skills found in ${DEST}"
else
    echo "lite-spec: removed from ${DEST}:${REMOVED}"
fi
