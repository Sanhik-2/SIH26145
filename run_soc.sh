#!/usr/bin/env bash
# Runs the CHRONOS React SOC Full-Stack Console regardless of working directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1
python dashboard/server.py "$@"
