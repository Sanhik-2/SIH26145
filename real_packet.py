#!/usr/bin/env python3
"""
Root entrypoint for CHRONOS Real Packet Network Automation Engine.
Enables running:
  python real_packet.py [options]
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from diode.real_packet import main

if __name__ == "__main__":
    main()
