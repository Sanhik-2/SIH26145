#!/usr/bin/env bash
# Runs the In-Zone Simplex Traffic Sender regardless of working directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1
python demo/inzone_sender.py "$@"
