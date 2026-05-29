from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from seed_demo import main  # noqa: E402


if __name__ == "__main__":
    main()
