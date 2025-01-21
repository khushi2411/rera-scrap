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

# Install lettuce_webdriver
try:
    import lettuce_webdriver
except ImportError:
    import pip
    pip.main(['install', 'lettuce_webdriver'])

def set_input_value(driver, element, value):
    """
    Sets the value of an input field using JavaScript to bypass potential restrictions.
    """
    driver.execute_script("arguments[0].value = arguments[1];", element, value)
    # Trigger any events associated with the input change
    driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", element)
    driver.execute_script("arguments[0].dispatchEvent(new Event('input'));", element)

def extract_outputData(serial_no, input_csv, output_json):
    outputData= []  # Move inside function to avoid global variable
    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--kiosk-printing")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-save-password-bubble")
    chrome_options.add_argument("--disable-browser-side-navigation")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 20)

    try:
        driver.get("https://rera.karnataka.gov.in/viewAllProjects")
        
        def initial_search():
            try:
                search_input = wait.until(EC.element_to_be_clickable((By.ID, 'projectDist')))
                print("Found and clickable 'projectDist' input field.")
            except TimeoutException:
                print("Failed to find 'projectDist' input field.")
                return False
            
            is_readonly = search_input.get_attribute('readonly')
            if is_readonly:
                print("'projectDist' input field is read-only. Setting value via JavaScript.")
                set_input_value(driver, search_input, 'Bengaluru Urban')
            else:
                try:
                    search_input.clear()
                except InvalidElementStateException:
                    print("Cannot clear 'projectDist' input field. Setting value via JavaScript.")
                    set_input_value(driver, search_input, 'Bengaluru Urban')
                search_input.send_keys('Bengaluru Urban')
                print("Entered 'Bengaluru Urban' into 'projectDist'.")

            try:
                search_button = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'btn-style')))
                print("Found search button.")
                search_button.click()
                print("Clicked search button.")
            except (TimeoutException, ElementClickInterceptedException) as e:
                print(f"Failed to click search button: {e}")
                return False

            try:
                wait.until(EC.presence_of_element_located((By.XPATH, '//table[@id="approvedTable"]')))
                print("Approved projects table loaded.")
                return True
            except TimeoutException:
                print("Approved projects table did not load in time.")
                return False

        if not initial_search():
            print("Initial search failed. Exiting script.")
            return

        search_terms = []
        try:
            with open(input_csv, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                for idx, row in enumerate(reader, start=1):
                    if idx >= serial_no and row and len(row) > 0 and row[0].strip():
                        search_terms.append(row[0].strip())
            print(f"Loaded {len(search_terms)} search terms from '{input_csv}'.")
        except FileNotFoundError:
            print(f"The file '{input_csv}' was not found.")
            return

        for term in search_terms:
            print(f"\nProcessing search term: '{term}'")
            try:
                search_bar = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="search"]')))
                driver.execute_script("arguments[0].scrollIntoView(true);", search_bar)
                search_bar.clear()
                search_bar.send_keys(term)
                search_bar.send_keys(u'\ue007')
                print(f"Entered '{term}' into search bar and pressed Enter.")

                try:
                    wait.until(EC.presence_of_element_located((By.XPATH, '//table[@id="approvedTable"]')))
                    print("Search results table loaded.")
                except TimeoutException:
                    print(f"Search results for '{term}' did not load in time.")
                    continue

                rows = driver.find_elements(By.XPATH, '//table[@id="approvedTable"]/tbody/tr')
                if not rows:
                    print(f"No data found for search term '{term}'.")
                    continue

                for row in rows:
                    try:
                        cells = row.find_elements(By.TAG_NAME, 'td')
                        if len(cells) < 5:
                            print(f"Row skipped due to insufficient data: {cells}")
                            continue
                        
                        

                        project_data = {
                            "Rera ID": cells[4].text.strip() if len(cells) > 4 else "N/A",
                            "Project Name": cells[0].text.strip() if len(cells) > 0 else "N/A",
                            
                        }

                        icon = row.find_element(By.XPATH, './/i[@class="fa fa-files-o" and @style="font-size:30px;color:#3948B1"]')
                        driver.execute_script("arguments[0].scrollIntoView(true);", icon)
                        
                        try:
                            icon.click()
                            print("Clicked on the details icon.")
                        except ElementClickInterceptedException:
                            driver.execute_script("arguments[0].click();", icon)
                            print("Clicked on the details icon using JavaScript.")

                        original_window = driver.current_window_handle
                        all_windows = driver.window_handles
                        if len(all_windows) > 1:
                            for window in all_windows:
                                if window != original_window:
                                    driver.switch_to.window(window)
                                    print("Switched to the new window/tab for project details.")
                                    break

                        try:
                            project_details_tab = wait.until(EC.element_to_be_clickable(
                                (By.XPATH, '//a[contains(text(),"Project Details")]')))
                            driver.execute_script("arguments[0].scrollIntoView(true);", project_details_tab)
                            project_details_tab.click()
                            print("Clicked on 'Project Details' tab.")
                        except TimeoutException:
                            print("Project Details tab not found, skipping this record.")
                            if len(driver.window_handles) > 1:
                                driver.close()
                                driver.switch_to.window(original_window)
                            else:
                                driver.back()
                            continue

                        try:
                            wait_short = WebDriverWait(driver, 5)
                            wait_short.until(EC.presence_of_all_elements_located(
                                (By.XPATH, '//div[@class="col-md-3 col-sm-6 col-xs-6"]/p')))
                            print("Project details loaded.")
                        except TimeoutException:
                            print("Project details not found within 5 seconds. Skipping this record.")
                            if len(driver.window_handles) > 1:
                                driver.close()
                                driver.switch_to.window(original_window)
                            else:
                                driver.back()
                            continue

                        # Extract Inventory Data
                        inventories = []
                        print("Processing inventory data...")
                        inventory_rows = driver.find_elements(By.XPATH, "//table[@class='table table-bordered table-striped table-condensed']/tbody/tr")
                        for inv_row in inventory_rows:
                            print(f"Processing row: {inv_row.text}") 
                            cells = inv_row.find_elements(By.TAG_NAME, 'td')
                            print(f"Row cells: {[cell.text for cell in cells]}")
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
                            else:
                                print(f"Skipping inventory row due to insufficient cells: {len(cells)}")
                        project_data["Inventories"] = inventories

                        # # Extract Tower Data
                        towers = []
                        print("Processing towers data...")
                        tower_rows = driver.find_elements(By.XPATH, "//table[@class='table table-bordered table-striped table-condensed']/tbody/tr")
                        for tower_row in tower_rows:
                            cells = tower_row.find_elements(By.TAG_NAME, 'td')
                            if len(cells) >= 8:
                                tower_data = {
                                    "Tower Name": cells[0].text.strip(),
                                    "No. of Floors": cells[1].text.strip(),
                                    "No. of Stilts": cells[2].text.strip(),
                                    "No. of Basement": cells[3].text.strip(),
                                    "Height of the Tower (In Meters)": cells[4].text.strip(),
                                    "Total No. of Units": cells[5].text.strip(),
                                    "No. of slab of super structure": cells[6].text.strip(),
                                    "Total No. of Parking": cells[7].text.strip(),
                                }
                                towers.append(tower_data)
                                
                        project_data["Towers"] = towers
                        project_data["Number_of_Towers"] = len(towers)

                        #FAR Sanctioned
                        FAR_Sanctioned = [] 
                        try:
                            far_sanctioned = driver.find_element(By.XPATH, '//div[@class="col-md-3 col-sm-6 col-xs-6"]/p').text.strip()
                            FAR_Sanctioned.append(far_sanctioned)
                        except NoSuchElementException:
                            FAR_Sanctioned.append("N/A")
                            project_data["FAR_Sanctioned"] = FAR_Sanctioned
                            
                       # Extract Internal Infrastructure
                        internal_infrastructure = []
                        internal_rows = driver.find_elements(By.XPATH, '//h1[contains(text(), "Internal Infrastructure")]/following-sibling::div/following-sibling::table[@class="table table-bordered table-striped table-condensed"]/tbody/tr')
                        for int_row in internal_rows:
                            cells = int_row.find_elements(By.TAG_NAME, 'td')
                            if len(cells) >= 3:
                                internal_data = {
                                    
                                    "Sl No": cells[0].text.strip(),
                                    "Work": cells[1].text.strip(),
                                    "Is Applicable": cells[2].text.strip(),
                                }

                                internal_infrastructure.append(internal_data)
                        project_data["Internal_Infrastructure"] = internal_infrastructure  

                        # Extract External Infrastructure
                        external_infrastructure = []
                        external_rows = driver.find_elements(By.XPATH, '//h1[contains(text(), "External Infrastructure")]/following-sibling::div/following-sibling::table[@class="table table-bordered table-striped table-condensed"]/tbody/tr')
                        for ext_row in external_rows:
                            cells = ext_row.find_elements(By.TAG_NAME, 'td')
                            if len(cells) >= 3:
                                external_data = {
                                    "Sl No": cells[0].text.strip(),
                                    "Work": cells[1].text.strip(),
                                    "Is Applicable": cells[2].text.strip(),
                                }
                                external_infrastructure.append(external_data)
                        project_data["External_Infrastructure"] = external_infrastructure
                       

                        # Extract Amenities
                        amenities = []
                        print("Processing amenities data...")
                        amenities_rows = driver.find_elements(By.XPATH, '//h1[contains(text(), "Amenities")]/following-sibling::div/following-sibling::table[@class="table table-bordered table-striped table-condensed"]/tbody/tr')
                        for amen_row in amenities_rows:
                            cells = amen_row.find_elements(By.TAG_NAME, 'td')
                            if len(cells) >= 3:
                                    # Process the row and append data
                                    amenities_data = {
                                        "Sl No": cells[0].text.strip(),
                                        "Work": cells[1].text.strip(),
                                        "Is Applicable": cells[2].text.strip(),
                                        "Area (Sq Mt)": cells[3].text.strip() if len(cells) > 3 else "N/A",}
                                    amenities.append(amenities_data)
                                    project_data["Amenities"] = amenities

                        outputData.append(project_data)

                        # Close the new tab and switch back to the original window
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
                continue

    finally:
        driver.quit()

        # Save all project data to JSON
        with open(output_json, 'w', encoding='utf-8') as json_file:
            json.dump(outputData, json_file, indent=4)
        print(f"Data saved to {output_json}")

if __name__ == "__main__":
    extract_outputData(1, './newDa.csv', './output.json')