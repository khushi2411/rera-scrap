import csv
import json
import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    ElementClickInterceptedException,
    UnexpectedAlertPresentException,
    InvalidElementStateException
)
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options

def set_input_value(driver, element, value):
    """Sets the value of an input field using JavaScript to bypass potential restrictions."""
    driver.execute_script("arguments[0].value = arguments[1];", element, value)
    driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", element)
    driver.execute_script("arguments[0].dispatchEvent(new Event('input'));", element)

def get_chrome_driver():
    """Initialize and return a new Chrome driver with options."""
    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--kiosk-printing")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-save-password-bubble")
    chrome_options.add_argument("--disable-browser-side-navigation")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    return webdriver.Chrome(options=chrome_options)

def initial_search(driver, wait):
    """Perform initial search setup for Bengaluru Urban."""
    try:
        search_input = wait.until(EC.element_to_be_clickable((By.ID, 'projectDist')))
        is_readonly = search_input.get_attribute('readonly')
        
        if is_readonly:
            set_input_value(driver, search_input, 'Bengaluru Urban')
        else:
            try:
                search_input.clear()
            except InvalidElementStateException:
                set_input_value(driver, search_input, 'Bengaluru Urban')
            search_input.send_keys('Bengaluru Urban')

        search_button = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'btn-style')))
        search_button.click()
        wait.until(EC.presence_of_element_located((By.XPATH, '//table[@id="approvedTable"]')))
        return True
    except Exception as e:
        print(f"Initial search failed: {e}")
        return False

def extract_inventory_data(driver, wait):
    """Extract inventory data from the current page."""
    inventories = []
    try:
        inventory_rows = driver.find_elements(By.XPATH, "//table[@class='table table-bordered table-striped table-condensed']/tbody/tr")
        
        for inv_row in inventory_rows:
            cells = inv_row.find_elements(By.TAG_NAME, "td")
            
            if len(cells) > 0 and cells[0].text.strip() == "Tower Name":
                break

            if len(cells) >= 6:
                inventory_data = {
                    "Sl No": cells[0].text.strip(),
                    "Type of Inventory": cells[1].text.strip(),
                    "No. of Inventory": cells[2].text.strip(),
                    "Carpet Area (Sq Mtr)": cells[3].text.strip(),
                    "Area of exclusive balcony/verandah (Sq Mtr)": cells[4].text.strip(),
                    "Area of exclusive open Terrace (Sq Mtr)": cells[5].text.strip(),
                }
                inventories.append(inventory_data)
    except Exception as e:
        print(f"Error extracting inventory data: {e}")
    return inventories

def extract_infrastructure_data(driver):
    """Extract infrastructure and amenities data."""
    sections = {"Internal Infrastructure": [], "External Infrastructure": [], "Amenities": []}
    current_section = "Internal Infrastructure"
    
    
    try:
        # Locate rows in the tables following the specific headers
        rows = driver.find_elements(By.XPATH, '//h1[contains(text(), "Internal Infrastructure")]/following-sibling::div/following-sibling::table[@class="table table-bordered table-striped table-condensed"]/tbody/tr')

        for row in rows:
            cells = row.find_elements(By.TAG_NAME, 'td')
            if len(cells) >= 3:
                processed_sl_no = set() 
                sl_no = cells[0].text.strip()

                # If "Sl No" is 1 and current section has data, switch section
                if sl_no == "1" and sections[current_section]:
                    if current_section == "Internal Infrastructure":
                        current_section = "External Infrastructure"
                    elif current_section == "External Infrastructure":
                        current_section = "Amenities"
                        processed_sl_no.clear()  # Reset processed_sl_no for new section
                    elif current_section == "Amenities":
                        # Stop processing if "Sl No 1" repeats in Amenities
                        break

                # Skip if the current "Sl No" has already been processed in this section
                if sl_no in processed_sl_no:
                    continue

                # Collect row data
                row_data = {
                    "Sl No": sl_no,
                    "Work": cells[1].text.strip(),
                    "Is Applicable": cells[2].text.strip(),
                }
                sections[current_section].append(row_data)
                processed_sl_no.add(sl_no)  # Mark this "Sl No" as processed
    except Exception as e:
        print(f"Error extracting infrastructure data: {e}")
    return sections

def process_search_term(term, driver, wait, output_data):
    """Process a single search term and return the extracted data."""
    try:
        search_bar = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="search"]')))
        driver.execute_script("arguments[0].scrollIntoView(true);", search_bar)
        search_bar.clear()
        search_bar.send_keys(term)
        search_bar.send_keys(u'\ue007')
        
        wait.until(EC.presence_of_element_located((By.XPATH, '//table[@id="approvedTable"]')))
        rows = driver.find_elements(By.XPATH, '//table[@id="approvedTable"]/tbody/tr')
        
        if not rows:
            print(f"No data found for search term '{term}'.")
            return
        
        for row in rows:
            try:
                cells = row.find_elements(By.TAG_NAME, 'td')
                if len(cells) < 5:
                    continue
                
                project_data = {
                    "Rera ID": term,
                    "Project Name": cells[4].text.strip() if len(cells) > 4 else "N/A",
                }
                
                # Click on details icon
                icon = row.find_element(By.XPATH, './/i[@class="fa fa-files-o" and @style="font-size:30px;color:#3948B1"]')
                driver.execute_script("arguments[0].scrollIntoView(true);", icon)
                driver.execute_script("arguments[0].click();", icon)
                
                # Handle window switching
                original_window = driver.current_window_handle
                all_windows = driver.window_handles
                for window in all_windows:
                    if window != original_window:
                        driver.switch_to.window(window)
                        break
                
                # Navigate to Project Details tab
                project_details_tab = wait.until(EC.element_to_be_clickable(
                    (By.XPATH, '//a[contains(text(),"Project Details")]')))
                project_details_tab.click()
                
                # Extract data
                project_data["Inventories"] = extract_inventory_data(driver, wait)
                infrastructure_data = extract_infrastructure_data(driver)
                project_data.update(infrastructure_data)
                
                output_data.append(project_data)
                
                # Close window and switch back
                if len(driver.window_handles) > 1:
                    driver.close()
                    driver.switch_to.window(original_window)
                
            except Exception as e:
                print(f"Error processing row: {e}")
                if len(driver.window_handles) > 1:
                    driver.close()
                    driver.switch_to.window(original_window)
                continue
                
    except Exception as e:
        print(f"Error processing term '{term}': {e}")
        return

def extract_outputData(serial_no, input_csv, output_json):
    """Main function to extract data for all search terms."""
    output_data = []
    
    # Read search terms
    try:
        with open(input_csv, 'r', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            search_terms = [row[0].strip() for idx, row in enumerate(reader, start=1)
                          if idx >= serial_no and row and len(row) > 0 and row[0].strip()]
    except FileNotFoundError:
        print(f"Input file '{input_csv}' not found.")
        return
    
    # Process each search term with a fresh driver instance
    for term in search_terms:
        print(f"\nProcessing search term: '{term}'")
        driver = None
        try:
            driver = get_chrome_driver()
            wait = WebDriverWait(driver, 20)
            
            # Initial setup
            driver.get("https://rera.karnataka.gov.in/viewAllProjects")
            if not initial_search(driver, wait):
                continue
                
            # Process the search term
            process_search_term(term, driver, wait, output_data)
            
        except Exception as e:
            print(f"Error during processing of term '{term}': {e}")
        finally:
            if driver:
                driver.quit()
            
        # Save progress after each term
        with open(output_json, 'w', encoding='utf-8') as json_file:
            json.dump(output_data, json_file, indent=4)
        print(f"Progress saved to {output_json} after processing term '{term}'")
        
        # Optional delay between terms to avoid overwhelming the server
        time.sleep(2)
    
    print(f"Processing completed. Final data saved to {output_json}")

if __name__ == "__main__":
    extract_outputData(1, './newDa.csv', './output.json')
