"""Compatibility entry point for the Cleanup Assistant web app.

It works directly from a source checkout as well as after installation.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from cleanup_assistant.web import main


if __name__ == "__main__":
    raise SystemExit(main())
