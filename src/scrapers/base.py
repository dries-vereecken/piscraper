"""
Base Scraper Class

Provides common functionality for all fitness studio scrapers.
"""

import json
import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from ..database.utils import get_connection, insert_run, insert_snapshots


class BaseScraper(ABC):
    """Base class for all fitness studio scrapers."""
    
    def __init__(self, source_name: str, headless: bool = True):
        """
        Initialize the scraper.
        
        Args:
            source_name: Name of the fitness studio/source
            headless: Whether to run browser in headless mode
        """
        self.source_name = source_name
        self.headless = headless
        self.driver = None
        self.run_id = None
        
    def setup_driver(self) -> webdriver.Chrome:
        """Set up Chrome WebDriver with optimal settings."""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless")
            
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/136.0.7103.92 Safari/537.36"
        )
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    
    def save_data(self, data: List[Dict[str, Any]]) -> bool:
        """
        Save scraped data to database.
        
        Args:
            data: List of scraped class/session data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with get_connection() as conn:
                # Insert run record
                git_sha = os.getenv("GITHUB_SHA")
                self.run_id = insert_run(conn, self.source_name, git_sha)
                
                # Insert snapshot data
                insert_snapshots(conn, self.run_id, self.source_name, data)
                
            print(f"✅ Saved {len(data)} records to database")
            return True
            
        except Exception as e:
            print(f"❌ Failed to save to database: {e}")
            
            # Fallback: save to JSON file
            return self._save_to_json_fallback(data)
    
    def _save_to_json_fallback(self, data: List[Dict[str, Any]]) -> bool:
        """
        Fallback method to save data to JSON file if database fails.
        
        Args:
            data: List of scraped data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scraped_data/{self.source_name}_{timestamp}.json"
            
            os.makedirs("scraped_data", exist_ok=True)
            
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str, ensure_ascii=False)
                
            print(f"💾 Fallback: Saved {len(data)} records to {filename}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to save to JSON: {e}")
            return False
    
    @abstractmethod
    def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape data from the fitness studio website.
        
        Returns:
            List of scraped class/session data
        """
        pass
    
    def run(self) -> bool:
        """
        Execute the complete scraping process.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            print(f"🚀 Starting {self.source_name} scraper...")
            
            # Set up driver
            self.driver = self.setup_driver()
            
            # Scrape data
            data = self.scrape()
            
            if not data:
                print("⚠️ No data scraped")
                return False
                
            # Save data
            success = self.save_data(data)
            
            print(f"✅ {self.source_name} scraping completed")
            return success
            
        except Exception as e:
            print(f"❌ {self.source_name} scraping failed: {e}")
            return False
            
        finally:
            if self.driver:
                self.driver.quit()
