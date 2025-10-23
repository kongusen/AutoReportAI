import os
import sys
from pathlib import Path


# Ensure the project root and backend package are discoverable regardless of checkout location.
ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
LOOM_DIR = ROOT_DIR / "loom-agent_副本"

for path in (BACKEND_DIR, ROOT_DIR, LOOM_DIR):
    str_path = str(path)
    if str_path not in sys.path:
        sys.path.insert(0, str_path)

# ensure `loom` package resolvable even if editable install not active
if "loom" not in sys.modules:
    try:
        __import__("loom")
    except ModuleNotFoundError:
        if LOOM_DIR.exists():
            sys.path.insert(0, str(LOOM_DIR))

# Default safe agent mode for tests unless explicitly overridden
os.environ.setdefault("NEW_AGENT_MODE", "local_stub")
