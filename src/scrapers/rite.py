#!/usr/bin/env python
# coding: utf-8

# In[3]:


from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from time import sleep

# Set up Chrome options
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run in headless mode
chrome_options.add_argument("--window-size=1920,1080")  # Desktop resolution
chrome_options.add_argument("--start-maximized")  # Maximize window
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.7103.92 Safari/537.36")  # Desktop user agent
chrome_options.add_argument('--disable-blink-features=AutomationControlled')  # Hide automation
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])  # Hide automation
chrome_options.add_experimental_option('useAutomationExtension', False)  # Hide automation

# Initialize the Chrome driver
driver = webdriver.Chrome(service=Service("/usr/local/bin/chromedriver"), options=chrome_options)

# Mask WebDriver to avoid detection
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

url = "https://rite.trainin.app/widget/schedule?trackingconsent=no"
driver.get(url)
print("WebDriver initialized successfully")


# In[4]:


import json
import re
from datetime import datetime
import os

try:
    # Wait for schedule items and headers to load
    wait = WebDriverWait(driver, 10)
    all_elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.ScheduleListGroup_header, div.ScheduleListItem.is-bookable")))

    # Initialize variables
    reform_classes = []
    current_date = ""
    today_date = datetime.now().strftime("%d/%m/%Y")

    # Process each element
    for element in all_elements:
        text = element.text.strip()

        # Check if the element is a date header
        if element.get_attribute("class").find("ScheduleListGroup_header") != -1:
            current_date = text
            continue

        # Check if the class is a REFORM class
        if "REFORM" in text:
            # Split the text into lines
            lines = text.split("\n")

            # Extract relevant information
            if len(lines) >= 6:  # Ensure there are enough lines to parse
                time = lines[0]
                name = lines[1]
                instructor = lines[2]
                address = lines[3]
                availability = lines[4]

                # Convert date format
                date = today_date if current_date == "TODAY" else current_date
                if "SATURDAY" in date or "SUNDAY" in date or "MONDAY" in date or "TUESDAY" in date or "WEDNESDAY" in date or "THURSDAY" in date or "FRIDAY" in date:
                    # Parse date like "SATURDAY 10 MAY"
                    date_obj = datetime.strptime(date, "%A %d %B")
                    # Set year to current year
                    date_obj = date_obj.replace(year=datetime.now().year)
                    # Format as dd/mm/yyyy
                    date = date_obj.strftime("%d/%m/%Y")

                # Create class dictionary
                class_info = {
                    "name": name,
                    "date": date,
                    "hour": time,
                    "address": address,
                    "instructor": instructor,
                    "availability": availability
                }

                reform_classes.append(class_info)

    # Create scraped_data directory if it doesn't exist
    os.makedirs("scraped_data", exist_ok=True)

    # Generate filename with current datetime
    current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"scraped_data/rite_schedule_{current_datetime}.json"

    # Count the number of classes scraped
    num_classes = len(reform_classes)
    print(f"Scraped {num_classes} classes")
    
    # Import db_utils for database operations
    from db_utils import write_snapshots
    
    # Write to database if DATABASE_URL is set
    if os.getenv("DATABASE_URL"):
        try:
            write_snapshots("rite", reform_classes)
            print("Successfully wrote data to database")
        except Exception as e:
            print(f"Error writing to database: {e}")
            # Fallback to JSON if database write fails
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(reform_classes, f, indent=2, ensure_ascii=False)
            print(f"Fallback: Saved schedule data to {filename}")
    else:
        # Fallback to JSON when running locally without DATABASE_URL
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(reform_classes, f, indent=2, ensure_ascii=False)
        print(f"Saved schedule data to {filename}")

    # Check if all expected fields are populated correctly
    expected_fields = ["name", "date", "hour", "address", "instructor", "availability"]
    missing_fields = {}

    for i, class_data in enumerate(reform_classes):
        for field in expected_fields:
            if field not in class_data or not class_data[field]:
                if field not in missing_fields:
                    missing_fields[field] = []
                missing_fields[field].append(i)

    if missing_fields:
        print("Warning: Some fields are missing or empty:")
        for field, indices in missing_fields.items():
            print(f"  - Field '{field}' is missing in {len(indices)} classes (indices: {indices[:5]}{'...' if len(indices) > 5 else ''})")
    else:
        print("All expected fields are populated correctly in all classes")

    # Print distinct locations if available
    distinct_locations = set(class_data.get("address", "") for class_data in reform_classes)
    print(f"\nFound {len(distinct_locations)} distinct locations:")
    for location in sorted(distinct_locations):
        if location:  # Only print non-empty locations
            print(f"  - {location}")




finally:
    # Close the browser
    driver.quit()


def main():
    """Main entry point for Rite scraper."""
    # The scraping code above runs when this script is executed
    pass


if __name__ == "__main__":
    main()


# In[ ]:




