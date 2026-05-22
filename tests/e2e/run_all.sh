#!/bin/bash
# run_all.sh
# Run all tests in the MiMinions project.
# This script executes pytest against all subdirectories in the tests folder.

# Change to the root of the project (one level up from tests/)
cd "$(dirname "$0")/.."

echo "Running all tests..."
pytest tests/ -v "$@"
