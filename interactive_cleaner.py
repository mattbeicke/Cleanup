"""Compatibility entry point for the Cleanup Assistant CLI.

It works directly from a source checkout as well as after installation.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from cleanup_assistant.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
