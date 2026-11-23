#!/usr/bin/env bash
# Runs the whole CI suite locally. Run it before opening a pull request.
#
# Requires node, python3 and uv.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> commit-message tooling"
[[ -d node_modules ]] || npm ci
npm test

echo
echo "==> published assets"
python3 scripts/check-assets.py
uv run --quiet scripts/render.py --check

echo
echo "All checks passed."
