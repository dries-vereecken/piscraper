"""
Scrapers Package

Web scrapers for various fitness studios and booking platforms.
"""

from .base import BaseScraper
from .koepel import KoepelScraper

__all__ = ["BaseScraper", "KoepelScraper"]
