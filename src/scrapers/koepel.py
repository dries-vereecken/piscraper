#!/usr/bin/env python3
"""
Koepel Studio Scraper

Scrapes fitness class schedules from Koepel studio website.
"""

import re
import time
from datetime import datetime
from typing import Any, Dict, List

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    TimeoutException,
    StaleElementReferenceException
)

from .base import BaseScraper


class KoepelScraper(BaseScraper):
    """Scraper for Koepel fitness studio."""
    
    def __init__(self, headless: bool = True):
        super().__init__("koepel", headless)
        self.url = "https://dekoepel.virtuagym.com//classes/week/?event_type=2&embedded=1"
        self.max_classes = 100
    
    def scrape(self) -> List[Dict[str, Any]]:
        """Scrape Koepel class data."""
        self.driver.get(self.url)
        print("WebDriver initialized successfully")
        
        class_details = []
        scraped_count = 0
        
        while scraped_count < self.max_classes:
            try:
                # Get all clickable event elements
                elements = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@onclick, 'openScheduleModal')]"))
                )
                
                for element in elements:
                    if scraped_count >= self.max_classes:
                        break
                    
                    try:
                        # Scroll into view and click
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", 
                            element
                        )
                        WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.ID, element.get_attribute("id")))
                        ).click()
                        
                        # Extract modal details
                        modal_content = WebDriverWait(self.driver, 10).until(
                            EC.visibility_of_element_located((By.CSS_SELECTOR, ".modal-content"))
                        )
                        details_text = modal_content.find_element(By.CSS_SELECTOR, ".modal-body").text
                        
                        # Parse class details
                        class_data = self._parse_class_details(details_text)
                        class_details.append(class_data)
                        scraped_count += 1
                        
                        # Close modal
                        self._close_modal()
                        
                    except (ElementClickInterceptedException, TimeoutException, StaleElementReferenceException) as e:
                        print(f"Error interacting with element: {e}")
                        self._recover_from_modal_error()
                        continue
                
                if scraped_count >= self.max_classes:
                    break
                
                # Navigate to next week
                if not self._click_next_week():
                    break
                    
            except TimeoutException:
                print("No more pages to scrape. Exiting...")
                break
            except ElementClickInterceptedException:
                print("Click intercepted, attempting recovery...")
                self._recover_from_modal_error()
                self.driver.refresh()
                time.sleep(3)
        
        print(f"Scraped {len(class_details)} classes")
        return class_details
    
    def _parse_class_details(self, details_text: str) -> Dict[str, Any]:
        """Parse class details from modal text."""
        details_lines = details_text.split('\n')
        
        filtered_details = {
            "date": "",
            "time": "",
            "capacity": "",
            "instructor": "",
            "scraped_at": datetime.now().isoformat()
        }
        
        for line in details_lines:
            line = line.strip()
            if not line or "Welkom bij" in line or "Tot snel!" in line:
                continue
                
            # Date pattern (Dutch weekdays)
            if re.match(r"^(maandag|dinsdag|woensdag|donderdag|vrijdag|zaterdag|zondag)\s+\d{2}\s+[a-z]+\s*$", line, re.IGNORECASE):
                filtered_details["date"] = line
            # Time pattern
            elif re.match(r"^\d{2}:\d{2}\s*-\s*\d{2}:\d{2}\s*$", line):
                filtered_details["time"] = line
            # Capacity pattern
            elif re.match(r"^\d+\s*/\s*\d+\s*$", line):
                filtered_details["capacity"] = line
            # Instructor pattern (names only, excluding class descriptions)
            elif re.match(r"^[A-Za-z\s]+$", line) and not any(
                keyword in line.lower() for keyword in ["pilates", "reformer", "core", "lichaam"]
            ):
                filtered_details["instructor"] = line
        
        return filtered_details
    
    def _close_modal(self):
        """Close the modal dialog with multiple fallback methods."""
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                # Method 1: Click close button
                close_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.close[data-dismiss='modal'][data-cy='modalDismissBtn']"))
                )
                self.driver.execute_script("arguments[0].click();", close_button)
                
                # Verify modal is closed
                if WebDriverWait(self.driver, 3).until(
                    EC.invisibility_of_element_located((By.CSS_SELECTOR, ".modal-content"))
                ):
                    break
                    
            except Exception:
                if attempt == 0:
                    # Method 2: Try XPath approach
                    try:
                        close_xpath = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[@class='close' and @data-dismiss='modal' and @data-cy='modalDismissBtn']"))
                        )
                        self.driver.execute_script("arguments[0].click();", close_xpath)
                    except Exception:
                        pass
                elif attempt == 1:
                    # Method 3: JavaScript dismiss
                    self.driver.execute_script("$('.modal').modal('hide');")
                    self.driver.execute_script("document.querySelector('.modal-backdrop')?.remove();")
                    self.driver.execute_script("document.body.classList.remove('modal-open');")
        
        # Ensure modal is fully closed
        WebDriverWait(self.driver, 5).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, ".modal-content"))
        )
        time.sleep(1)
    
    def _recover_from_modal_error(self):
        """Recover from modal interaction errors."""
        try:
            self.driver.execute_script("$('.modal').modal('hide');")
            self.driver.execute_script("document.querySelector('.modal-backdrop')?.remove();")
            self.driver.execute_script("document.body.classList.remove('modal-open');")
            WebDriverWait(self.driver, 5).until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, ".modal-content"))
            )
            time.sleep(1)
        except Exception:
            pass
    
    def _click_next_week(self) -> bool:
        """Navigate to next week. Returns True if successful, False if no more pages."""
        try:
            next_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'volgende')]"))
            )
            
            # Clear any modal backdrop
            try:
                backdrop = self.driver.find_element(By.CSS_SELECTOR, ".modal-backdrop")
                if backdrop:
                    self.driver.execute_script("document.querySelector('.modal-backdrop').remove();")
                    self.driver.execute_script("document.body.classList.remove('modal-open');")
                    time.sleep(0.5)
            except Exception:
                pass
            
            self.driver.execute_script("arguments[0].click();", next_button)
            time.sleep(4)
            return True
            
        except TimeoutException:
            return False


def main():
    """Main entry point for the Koepel scraper."""
    scraper = KoepelScraper(headless=True)
    success = scraper.run()
    return success


if __name__ == "__main__":
    main()
