#!/usr/bin/env python
# coding: utf-8

# In[20]:


from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException, StaleElementReferenceException
from time import sleep
from datetime import datetime
import json
import time
import re

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

url = "https://dekoepel.virtuagym.com//classes/week/?event_type=2&embedded=1"
driver.get(url)
print("WebDriver initialized successfully")


# In[21]:


import os
# Create scraped_data folder if it doesn't exist
output_dir = "scraped_data"
os.makedirs(output_dir, exist_ok=True)

# List to store scraped class details
class_details = []
scraped_count = 0
max_classes = 100

while True:
    try:
        # Get all clickable event elements
        elements = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@onclick, 'openScheduleModal')]"))
        )

        for element in elements:
            if scraped_count >= max_classes:
                break  # Stop if 100 classes are scraped

            try:
                # Scroll into view and click the current element
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, element.get_attribute("id")))).click()

                # Extract the modal details
                modal_content = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, ".modal-content"))
                )
                details_text = modal_content.find_element(By.CSS_SELECTOR, ".modal-body").text

                # Filter and structure the details
                details_lines = details_text.split('\n')
                filtered_details = {
                    "date": "",
                    "time": "",
                    "capacity": "",
                    "instructor": ""
                }

                # Extract relevant fields using regex and line parsing
                for line in details_lines:
                    line = line.strip()
                    if not line or "Welkom bij" in line or "Tot snel!" in line:
                        continue  # Skip irrelevant or promotional text
                    if re.match(r"^(maandag|dinsdag|woensdag|donderdag|vrijdag|zaterdag|zondag)\s+\d{2}\s+[a-z]+\s*$", line, re.IGNORECASE):
                        filtered_details["date"] = line
                    elif re.match(r"^\d{2}:\d{2}\s*-\s*\d{2}:\d{2}\s*$", line):
                        filtered_details["time"] = line
                    elif re.match(r"^\d+\s*/\s*\d+\s*$", line):
                        filtered_details["capacity"] = line
                    elif re.match(r"^[A-Za-z\s]+$", line) and not any(keyword in line.lower() for keyword in ["pilates", "reformer", "core", "lichaam"]):
                        filtered_details["instructor"] = line

                class_details.append(filtered_details)
                scraped_count += 1
                # print(f"Scraped class {scraped_count}: {filtered_details}")

                # Improved modal closing with multiple fallback methods
                max_close_attempts = 3
                for attempt in range(max_close_attempts):
                    try:
                        # Method 1: Try clicking the close button directly
                        close_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.close[data-dismiss='modal'][data-cy='modalDismissBtn']"))
                        )
                        driver.execute_script("arguments[0].click();", close_button)

                        # Verify modal is closed
                        if WebDriverWait(driver, 3).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, ".modal-content"))):
                            break
                    except Exception:
                        if attempt == 0:
                            # Method 2: Try clicking by XPath
                            try:
                                close_xpath = WebDriverWait(driver, 3).until(
                                    EC.element_to_be_clickable((By.XPATH, "//button[@class='close' and @data-dismiss='modal' and @data-cy='modalDismissBtn']"))
                                )
                                driver.execute_script("arguments[0].click();", close_xpath)
                            except Exception:
                                pass
                        elif attempt == 1:
                            # Method 3: Try pressing Escape key
                            webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                        else:
                            # Method 4: Last resort - execute dismiss via JavaScript
                            driver.execute_script("$('.modal').modal('hide');")
                            driver.execute_script("document.querySelector('.modal-backdrop')?.remove();")
                            driver.execute_script("document.body.classList.remove('modal-open');")

                # Ensure modal is fully closed before continuing
                WebDriverWait(driver, 5).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, ".modal-content")))
                time.sleep(1)

            except ElementClickInterceptedException:
                print("Modal interaction issue, attempting recovery...")
                driver.execute_script("$('.modal').modal('hide');")
                driver.execute_script("document.querySelector('.modal-backdrop')?.remove();")
                driver.execute_script("document.body.classList.remove('modal-open');")
                WebDriverWait(driver, 5).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, ".modal-content")))
                time.sleep(1)
            except (TimeoutException, StaleElementReferenceException) as e:
                print("Error interacting with modal:", e)
                continue

        if scraped_count >= max_classes:
            break  # Exit the outer loop if 100 classes are scraped

        # Click the 'volgende' button to go to next week
        next_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'volgende')]"))
        )

        # Make sure no modal backdrop is present before clicking next button
        try:
            backdrop = driver.find_element(By.CSS_SELECTOR, ".modal-backdrop")
            if backdrop:
                driver.execute_script("document.querySelector('.modal-backdrop').remove();")
                driver.execute_script("document.body.classList.remove('modal-open');")
                time.sleep(0.5)
        except:
            pass

        driver.execute_script("arguments[0].click();", next_button)
        time.sleep(4)

    except TimeoutException:
        print("No more pages to scrape. Exiting...")
        break
    except ElementClickInterceptedException as e:
        print("Click intercepted, attempting recovery...")
        driver.execute_script("$('.modal').modal('hide');")
        driver.execute_script("document.querySelector('.modal-backdrop')?.remove();")
        driver.execute_script("document.body.classList.remove('modal-open');")
        time.sleep(1)
        driver.refresh()
        time.sleep(3)

# Save the results to a JSON file
output_file = os.path.join(output_dir, f"koepel_schedule_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(class_details, f, ensure_ascii=False, indent=4)
# Count the number of classes scraped
num_classes = len(class_details)
print(f"Scraped {num_classes} classes")

# Check if all expected fields are populated correctly
expected_fields = ["date", "time", "capacity", "instructor"]
missing_fields = {}

for i, class_data in enumerate(class_details):
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
if any("location" in class_data for class_data in class_details):
    distinct_locations = set(class_data.get("location", "") for class_data in class_details if "location" in class_data)
    print(f"\nFound {len(distinct_locations)} distinct locations:")
    for location in sorted(distinct_locations):
        if location:  # Only print non-empty locations
            print(f"  - {location}")


print(f"Done! Saved {scraped_count} classes to {output_file}")
driver.quit()
