import sys
from pathlib import Path

# src layout without requiring an editable install for `pytest` runs
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
