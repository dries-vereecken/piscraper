#!/usr/bin/env python
# coding: utf-8

# In[2]:


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
# chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")  # Desktop user agent

# Initialize the Chrome driver
driver = webdriver.Chrome(service=Service("/usr/local/bin/chromedriver"), options=chrome_options)


# In[3]:


# URL to scrape
url = "https://www.rowreformer.com/schedule"
driver.get(url)
print("WebDriver initialized successfully")

# Wait for page to load
sleep(10)
# Find all week cards for current week
week_cards = driver.find_elements(By.CSS_SELECTOR, ".bs-week-card")

# Get current date and calculate dates for the weeks
from datetime import datetime, timedelta
current_date = datetime.now()

# Get to Monday of current week
monday = current_date - timedelta(days=current_date.weekday())

# Initialize variables
days_of_week = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"]
num_days = 7
schedule_data = {}

# Process 4 weeks (current + 3 upcoming)
for week_num in range(1, 5):
    # Calculate dates for this week
    week_dates = [(monday + timedelta(days=i + (7 * (week_num-1)))) for i in range(7)]

    # Initialize week in schedule data
    for i, day in enumerate(days_of_week):
        date = week_dates[i]
        schedule_data[f"Week {week_num} {day}"] = {
            'date': date.strftime('%d/%m/%Y'),
            'classes': []
        }

    # Process each week card
    week_cards = driver.find_elements(By.CSS_SELECTOR, ".bs-week-card")

    for week_card in week_cards:
        # Get all blocks in this card
        blocks = week_card.find_elements(By.CSS_SELECTOR, ".bs-week__cardMode__offerRow__item, .bs-week__cardMode__offerRow__offer-wrapper")

        # Group blocks by day
        for block_index in range(0, len(blocks), num_days):
            day_blocks = blocks[block_index:block_index + num_days]

            # Process each day's block
            for day_index, block in enumerate(day_blocks):
                if day_index >= len(days_of_week):
                    break

                # Extract text elements from this block
                text_elements = block.find_elements(By.XPATH, ".//*[text()]")

                # Build class info dictionary
                class_info = {}
                current_info = []

                # Process text elements to remove duplicates
                seen_texts = set()
                for element in text_elements:
                    text = element.text.strip()
                    if text and text not in seen_texts:
                        seen_texts.add(text)
                        if text in ['RESERVEER', 'WACHTLIJST', "BINNENKORT BESCHIKBAAR"]:
                            class_info['status'] = text
                            if current_info:
                                class_info['details'] = current_info
                                schedule_data[f"Week {week_num} {days_of_week[day_index]}"]['classes'].append(class_info)
                                class_info = {}
                                current_info = []
                        else:
                            current_info.append(text)

                # Add any remaining info
                if current_info:
                    class_info['details'] = current_info
                    if 'status' not in class_info:
                        class_info['status'] = None
                    schedule_data[f"Week {week_num} {days_of_week[day_index]}"]['classes'].append(class_info)

    # Click next week button if not on last week
    if week_num < 4:
        next_week_button = driver.find_element(By.CSS_SELECTOR, "button.bs-marketplace-date-picker__right-button")
        next_week_button.click()

        # Wait for next week's data to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".bs-week-card"))
        )

# Print JSON structure
import json
# Generate filename with current datetime
current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"scraped_data/row_schedule_{current_datetime}.json"

# Save to JSON file
with open(filename, "w", encoding="utf-8") as f:
    json.dump(schedule_data, f, indent=2, ensure_ascii=False)

print(f"Data has been saved to {filename}")


driver.quit()

