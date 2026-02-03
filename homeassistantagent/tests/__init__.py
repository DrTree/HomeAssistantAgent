from __future__ import annotations

import sys
from pathlib import Path

tests_dir = Path(__file__).resolve().parent
package_root = tests_dir.parent
if str(package_root) not in sys.path:
    sys.path.insert(0, str(package_root))
