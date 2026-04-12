#!/bin/bash
# Roll It & Bowl It launch script
# Uses the project's .venv if present, otherwise falls back to system python3.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f ".venv/bin/python" ]; then
    .venv/bin/python start.py
else
    python3 start.py
fi
