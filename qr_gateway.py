#!/usr/bin/env python3
"""
Root convenience wrapper for CHRONOS Optical Data Diode QR Gateway.
Enables running:
  python qr_gateway.py [options]
"""
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from diode.qr_gateway import main

if __name__ == "__main__":
    main()
