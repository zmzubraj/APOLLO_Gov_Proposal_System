import sys, pathlib
root = pathlib.Path(__file__).resolve().parents[1]
sys.path.extend([str(root), str(root / "src")])
