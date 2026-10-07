#!/usr/bin/env bash
set -euo pipefail

# Build settings live in miminions-cli.spec, which CI uses too. Do not add
# PyInstaller flags here; see memory/past/adrs/0008-cli-binary-build-flags.md.
cd "$(dirname "$0")/.."

# `all` is required, not optional: a standalone-binary user cannot install an
# extra later, so vector memory must be bundled or it is unreachable forever.
uv sync --extra all --extra cli-build
uv run pyinstaller --clean miminions-cli.spec

echo "CLI binary generated at: dist/miminions-cli"
