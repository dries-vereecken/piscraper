"""
Scrapers Package

Web scrapers for various fitness studios and booking platforms.
"""

import sys
import os

# Add the project root to Python path to handle imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from .base import BaseScraper
    from .koepel import KoepelScraper
except ImportError:
    # Fallback for direct script execution
    from src.scrapers.base import BaseScraper
    from src.scrapers.koepel import KoepelScraper

__all__ = ["BaseScraper", "KoepelScraper"]
