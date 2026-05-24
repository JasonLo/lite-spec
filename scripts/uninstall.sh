#!/bin/sh
# lite-spec uninstaller — removes the spec-* skills from a Claude Code skills dir.
#
# One-liner (prompts for location; default: per-project):
#   curl -LsSf https://raw.githubusercontent.com/JasonLo/lite-spec/main/scripts/uninstall.sh | sh
#
# Non-interactive — choose explicitly:
#   curl -LsSf .../uninstall.sh | sh -s -- --project   # ./.claude/skills/
#   curl -LsSf .../uninstall.sh | sh -s -- --global    # ~/.claude/skills/

set -eu

MODE=""

usage() {
    cat <<EOF
lite-spec uninstaller

Usage:
  uninstall.sh [--project | --global]

Options:
  --project      remove from \$PWD/.claude/skills/ (interactive default)
  --global       remove from \$HOME/.claude/skills/
  -h, --help     show this message

With no flag, the uninstaller prompts you to choose project (default) or global.
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --global)  MODE="global"; shift ;;
        --project) MODE="project"; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "error: unknown argument: $1" >&2; usage >&2; exit 2 ;;
    esac
done

if [ -z "$MODE" ]; then
    MODE="project"
    # Subshell isolates redirection failure: under dash + `set -e`, a failed
    # `> /dev/tty` aborts the parent script; running it in `( ... )` keeps us alive.
    if ( : > /dev/tty ) 2>/dev/null; then
        printf 'Uninstall lite-spec from where?\n  [P]roject  ./.claude/skills/  (default)\n  [G]lobal   ~/.claude/skills/\nChoice [P/g]: ' > /dev/tty
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

REMOVED=""
for skill in "$DEST"/spec-*; do
    [ -d "$skill" ] || continue
    name="$(basename "$skill")"
    rm -rf "$skill"
    REMOVED="${REMOVED} ${name}"
done

if [ -z "$REMOVED" ]; then
    echo "lite-spec: no spec-* skills found in ${DEST}"
else
    echo "lite-spec: removed from ${DEST}:${REMOVED}"
fi
