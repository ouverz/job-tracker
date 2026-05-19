"""Pytest configuration — makes the app package importable from backend/tests/."""

import sys
from pathlib import Path

# Add backend/ to sys.path so `from app.scrapers.runner import ...` works
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
