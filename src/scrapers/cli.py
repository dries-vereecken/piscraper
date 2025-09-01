#!/usr/bin/env python3
"""
Command Line Interface for Schedule Scrapers

Provides a unified CLI for running individual scrapers or all scrapers.
"""

import argparse
import sys
from typing import Dict, Type

from .base import BaseScraper
from .koepel import KoepelScraper


# Registry of available scrapers
SCRAPERS: Dict[str, Type[BaseScraper]] = {
    "koepel": KoepelScraper,
    # Note: Other scrapers need to be refactored to inherit from BaseScraper
    # "coolcharm": CoolCharmScraper,
    # "rite": RiteScraper,
    # "rowreformer": RowReformerScraper,
}


def run_scraper(scraper_name: str, headless: bool = True) -> bool:
    """
    Run a specific scraper.
    
    Args:
        scraper_name: Name of the scraper to run
        headless: Whether to run in headless mode
        
    Returns:
        True if successful, False otherwise
    """
    if scraper_name not in SCRAPERS:
        print(f"❌ Unknown scraper: {scraper_name}")
        print(f"Available scrapers: {', '.join(SCRAPERS.keys())}")
        return False
    
    scraper_class = SCRAPERS[scraper_name]
    scraper = scraper_class(headless=headless)
    
    return scraper.run()


def run_all_scrapers(headless: bool = True) -> bool:
    """
    Run all available scrapers.
    
    Args:
        headless: Whether to run in headless mode
        
    Returns:
        True if all successful, False if any failed
    """
    success_count = 0
    total_count = len(SCRAPERS)
    
    print(f"🚀 Running {total_count} scrapers...")
    
    for scraper_name in SCRAPERS:
        print(f"\n{'='*50}")
        print(f"Running {scraper_name} scraper...")
        
        if run_scraper(scraper_name, headless):
            success_count += 1
            print(f"✅ {scraper_name} completed successfully")
        else:
            print(f"❌ {scraper_name} failed")
    
    print(f"\n{'='*50}")
    print(f"Summary: {success_count}/{total_count} scrapers completed successfully")
    
    return success_count == total_count


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Schedule Scraper CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  schedule-scraper koepel              # Run Koepel scraper
  schedule-scraper --all               # Run all scrapers
  schedule-scraper koepel --no-headless # Run with visible browser
        """
    )
    
    parser.add_argument(
        "scraper",
        nargs="?",
        choices=list(SCRAPERS.keys()),
        help="Name of the scraper to run"
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all available scrapers"
    )
    
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Run with visible browser (useful for debugging)"
    )
    
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available scrapers"
    )
    
    args = parser.parse_args()
    
    # List scrapers
    if args.list:
        print("Available scrapers:")
        for name in SCRAPERS:
            print(f"  - {name}")
        return
    
    # Validate arguments
    if not args.all and not args.scraper:
        parser.error("Must specify either a scraper name or --all")
        return
    
    if args.all and args.scraper:
        parser.error("Cannot specify both --all and a specific scraper")
        return
    
    headless = not args.no_headless
    
    # Run scrapers
    if args.all:
        success = run_all_scrapers(headless)
    else:
        success = run_scraper(args.scraper, headless)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
