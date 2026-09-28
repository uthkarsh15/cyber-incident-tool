import sys
from pathlib import Path

# Add project root and backend to sys.path so tests can import both 'backend.*' and 'app.*'
THIS_DIR = Path(__file__).resolve().parent
if THIS_DIR.parent.name == "backend":
    BACKEND_DIR = THIS_DIR.parent
    ROOT_DIR = BACKEND_DIR.parent
else:
    ROOT_DIR = THIS_DIR.parent
    BACKEND_DIR = ROOT_DIR / "backend"

for path in [str(BACKEND_DIR), str(ROOT_DIR)]:
    if path not in sys.path:
        sys.path.insert(0, path)

