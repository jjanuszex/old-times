#!/usr/bin/env python3
"""
Main entry point for the asset pipeline.
Can be run directly or imported as a module.
"""

import sys
from pathlib import Path

# Add the scripts directory to Python path so we can import asset_pipeline
scripts_dir = Path(__file__).parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from asset_pipeline.cli import app

if __name__ == "__main__":
    app()