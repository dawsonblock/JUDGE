#!/usr/bin/env bash
# Guard: fail if any .pyc or __pycache__ files are committed to git.
set -euo pipefail

if git ls-files --cached | grep -qE '\.pyc$|__pycache__'; then
    echo "ERROR: Committed bytecode files detected:"
    git ls-files --cached | grep -E '\.pyc$|__pycache__'
    exit 1
fi
echo "OK: No committed bytecode files"
