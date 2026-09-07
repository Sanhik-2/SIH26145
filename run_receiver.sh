#!/usr/bin/env bash
# Runs the Diode Scanner AI Ingestion Receiver regardless of working directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1
python demo/scan_receiver.py "$@"
