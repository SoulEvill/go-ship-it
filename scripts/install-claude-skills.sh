#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="$ROOT/.claude/skills"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      TARGET="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

mkdir -p "$TARGET"

for skill in "$ROOT"/skills/*; do
  [[ -d "$skill" ]] || continue
  name="$(basename "$skill")"
  rm -rf "$TARGET/$name"
  cp -R "$skill" "$TARGET/$name"
done

echo "Installed GoShipit Claude skills to $TARGET"
