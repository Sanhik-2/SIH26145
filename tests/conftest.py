import sys
from pathlib import Path

# make "from models.njode import ..." work when running pytest from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
