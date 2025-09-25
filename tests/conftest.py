import os
import sys


# Ensure the backend package root is on sys.path so `import app...` works in tests
BACKEND_ROOT = "/Users/shan/work/uploads/AutoReportAI/backend"
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

# Default safe agent mode for tests unless explicitly overridden
os.environ.setdefault("NEW_AGENT_MODE", "local_stub")


