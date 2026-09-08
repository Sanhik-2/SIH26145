#!/usr/bin/env python3
"""
Root convenience entry point for CHRONOS Red-Team Cyber Warfare Console.
Usage:
  python redteam.py                  # Interactive numbered menu (Target: 192.168.137.1)
  python redteam.py <IP>             # Interactive menu for custom IP
  python redteam.py <1-9> [IP]       # Direct attack execution by number
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from diode.redteam_arch import main

if __name__ == "__main__":
    main()
