#!/usr/bin/env bash
set -euo pipefail

uv sync --extra cli-build
uv run pyinstaller --clean --onefile --name miminions-cli --paths src main.py

echo "CLI binary generated at: dist/miminions-cli"