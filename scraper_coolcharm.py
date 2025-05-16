#!/usr/bin/env python
# coding: utf-8

# In[68]:


from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from time import sleep
from datetime import datetime
import json

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

url = "https://coolcharmpilates.trainin.app/widget/schedule"
driver.get(url)
print("WebDriver initialized successfully")


# In[69]:


# Initialize list to store all classes
all_classes = []

# Scrape two weeks of data
for week in range(4):
    # Wait for the schedule list to load
    wait = WebDriverWait(driver, 10)
    schedule_list = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "ScheduleListGroup")))

    # Find all schedule groups
    schedule_groups = driver.find_elements(By.CLASS_NAME, "ScheduleListGroup")

    # Iterate through each group
    for group in schedule_groups:
        # Get the date header and convert to standard format
        date_text = group.find_element(By.CLASS_NAME, "ScheduleListGroup_date").text.strip()

        # Parse the date (e.g., "SATURDAY 10 MAY" to "10/05/2025")
        try:
            day_month = ' '.join(date_text.split()[1:])  # Get "10 MAY"
            # Handle month names properly - some months have different formats
            date_parts = day_month.split()
            day = date_parts[0]
            month = date_parts[1].capitalize()
            
            # Use locale-independent month parsing
            month_dict = {
                'JANUARY': '01', 'JAN': '01',
                'FEBRUARY': '02', 'FEB': '02',
                'MARCH': '03', 'MAR': '03',
                'APRIL': '04', 'APR': '04',
                'MAY': '05',
                'JUNE': '06', 'JUN': '06',
                'JULY': '07', 'JUL': '07',
                'AUGUST': '08', 'AUG': '08',
                'SEPTEMBER': '09', 'SEP': '09',
                'OCTOBER': '10', 'OCT': '10',
                'NOVEMBER': '11', 'NOV': '11',
                'DECEMBER': '12', 'DEC': '12'
            }
            
            month_num = month_dict.get(month.upper(), '00')
            date = f"{int(day):02d}/{month_num}/2025"  # Format to "10/05/2025"
        except (ValueError, KeyError) as e:
            print(f"Error parsing date {date_text}: {e}")
            date = date_text  # Fallback to original text if parsing fails

        # Find all class items in this group
        class_items = group.find_elements(By.CLASS_NAME, "ScheduleListItem")

        # Process each class
        for item in class_items:
            try:
                location = item.find_element(By.CLASS_NAME, "ScheduleListItem_location").text.strip()
            except NoSuchElementException:
                location = "Location not specified"

            try:
                availability = item.find_element(By.CLASS_NAME, "ScheduleListItem_participants").find_element(By.CLASS_NAME, "level-left").text.strip()
            except NoSuchElementException:
                availability = "Not specified"

            try:
                booking_status = item.find_element(By.CLASS_NAME, "SessionBookButton").text.strip()
            except NoSuchElementException:
                booking_status = "Unknown"

            class_data = {
                "date": date,
                "time": item.find_element(By.CLASS_NAME, "ScheduleListItem_time").text.split('\n')[0].strip(),
                "class_name": item.find_element(By.CLASS_NAME, "ScheduleListItem_title").text.strip(),
                "location": location,
                "availability": availability,
                "booking_status": booking_status
            }
            all_classes.append(class_data)

    # Click next week button if not on last iteration
    if week < 3:
        next_week_button = driver.find_element(By.XPATH, "/html/body/div/div/div/div/div[2]/div/div/div/div[3]/span/i")
        next_week_button.click()
        print("Clicked next week button")
        sleep(5)  # Wait for new data to load

# Convert to JSON structure
# print(json.dumps({"classes": all_classes}, indent=2))

driver.quit()


# In[70]:


url = "https://coolcharmpilates-studios.trainin.app/widget/schedule"
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

driver.get(url)
print("WebDriver initialized successfully")


# In[71]:


# Scrape four weeks of data
for week in range(3):
    # Wait for the schedule list to load
    wait = WebDriverWait(driver, 10)
    schedule_list = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "ScheduleListGroup")))

    # Find all schedule groups
    schedule_groups = driver.find_elements(By.CLASS_NAME, "ScheduleListGroup")

    # Process each schedule group
    for group in schedule_groups:
        # Get the date header and convert to standard format
        date_text = group.find_element(By.CSS_SELECTOR, "div.ScheduleListGroup div.ScheduleListGroup_date.heading").text.strip()
        
        # Parse the date with special handling for "TODAY"
        try:
            if date_text.upper() == "TODAY":
                date_obj = datetime.now()
            else:
                # Extract day and month (e.g., "SATURDAY 10 MAY" -> "10 MAY")
                day_month = ' '.join(date_text.split()[1:])
                # Parse with year 2025 (based on context)
                date_obj = datetime.strptime(f"{day_month} 2025", "%d %b %Y")
            # Format to "10/05/2025"
            date = date_obj.strftime("%d/%m/%Y")
        except ValueError as e:
            print(f"Error parsing date {date_text}: {e}")
            date = date_text  # Fallback to default date if parsing fails
            
        # Find all class items in this group
        class_items = group.find_elements(By.CLASS_NAME, "ScheduleListItem")
        
        # Process each class
        for item in class_items:
            class_data = {
                "type": item.find_element(By.CLASS_NAME, "ScheduleListItem_title").text.strip(),
                "time": item.find_element(By.CLASS_NAME, "ScheduleListItem_time").text.strip(),
                "location": item.find_element(By.CLASS_NAME, "ScheduleListItem_location").find_element(By.TAG_NAME, "span").text.strip(),
                "status": item.find_element(By.CLASS_NAME, "ScheduleListItem_bookColumn").find_element(By.CLASS_NAME, "SessionBookButton").text.strip(),
                "date": date,
            }
            all_classes.append(class_data)

    # Click next week button if not on last iteration
    if week < 2:
        next_week_button = driver.find_element(By.XPATH, "/html/body/div/div/div/div/div[2]/div/div/div/div[3]/span/i")
        next_week_button.click()
        print("Clicked next week button")
        sleep(5)  # Wait for new data to load

driver.quit()


# In[72]:


import os
# Create directory if it doesn't exist
current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
output_dir = "scraped_data"
os.makedirs(output_dir, exist_ok=True)

# Save JSON file
output_file = os.path.join(output_dir, f"coolcharm_schedule_{current_datetime}.json")
with open(output_file, "w") as f:
    json.dump(all_classes, f, indent=2)

# Count the number of classes scraped
num_classes = len(all_classes)
print(f"Scraped {num_classes} classes")

# Check if all expected fields are populated correctly
expected_fields = ["name", "date", "hour", "address", "instructor", "booking_status"]
missing_fields = {}

for i, class_data in enumerate(all_classes):
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

# Print distinct addresses
distinct_addresses = set(class_data["address"] for class_data in all_classes)
print(f"\nFound {len(distinct_addresses)} distinct locations:")
for address in sorted(distinct_addresses):
    print(f"  - {address}")

print(f"Saved schedule data to {output_file}")


# In[ ]:




