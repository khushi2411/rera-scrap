import csv
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
    """
    Sets the value of an input field using JavaScript to bypass potential restrictions.
    """
    driver.execute_script("arguments[0].value = arguments[1];", element, value)
    # Trigger any events associated with the input change
    driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", element)
    driver.execute_script("arguments[0].dispatchEvent(new Event('input'));", element)

def process_data_from_serial(serial_no):
    # Set Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--kiosk-printing")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-save-password-bubble")
    chrome_options.add_argument("--disable-browser-side-navigation")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    # Uncomment the following line to run Chrome in headless mode
    # chrome_options.add_argument("--headless")

    # Initialize Chrome webdriver with options
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 20)

    try:
        # URL of the website
        URL = 'https://rera.karnataka.gov.in/viewAllProjects'
        driver.get(URL)
        print("Navigated to the main URL.")

        # Function to perform initial search setup
        def initial_search():
            try:
                # Wait until the projectDist input is clickable
                search_input = wait.until(EC.element_to_be_clickable((By.ID, 'projectDist')))
                print("Found and clickable 'projectDist' input field.")
            except TimeoutException:
                print("Failed to find 'projectDist' input field.")
                return False

            # Check if the input field is read-only
            is_readonly = search_input.get_attribute('readonly')
            if is_readonly:
                print("'projectDist' input field is read-only. Setting value via JavaScript.")
                set_input_value(driver, search_input, 'Bengaluru Urban')
            else:
                # Clear the field and enter 'Bengaluru Urban'
                try:
                    search_input.clear()
                except InvalidElementStateException:
                    print("Cannot clear 'projectDist' input field. Setting value via JavaScript.")
                    set_input_value(driver, search_input, 'Bengaluru Urban')
                search_input.send_keys('Bengaluru Urban')
                print("Entered 'Bengaluru Urban' into 'projectDist'.")

            # Find and click the search button
            try:
                search_button = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'btn-style')))
                print("Found search button.")
                search_button.click()
                print("Clicked search button.")
            except (TimeoutException, ElementClickInterceptedException) as e:
                print(f"Failed to click search button: {e}")
                return False

            # Wait for the table to load
            try:
                wait.until(EC.presence_of_element_located((By.XPATH, '//table[@id="approvedTable"]')))
                print("Approved projects table loaded.")
                return True
            except TimeoutException:
                print("Approved projects table did not load in time.")
                return False

        # Perform initial search
        if not initial_search():
            print("Initial search failed. Exiting script.")
            return

        # Read the search terms from the existing CSV file, ignoring empty lines
        search_terms = []
        try:
            with open('newDa.csv', 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                for idx, row in enumerate(reader, start=1):
                    if idx >= serial_no and row and row[0].strip():  # Ensure the row is not empty
                        search_terms.append(row[0].strip())
            print(f"Loaded {len(search_terms)} search terms from 'newDa.csv'.")
        except FileNotFoundError:
            print("The file 'newDa.csv' was not found.")
            return

        # Open the new CSV file in append mode
        with open('new_data_.csv', 'a', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                's_no', 'ack_no', 'reg_no', 'promoter_name', 'project_name', 
                'status', 'district', 'taluk', 'approved_on', 'proposed_completion_date', 
                'covid_extension_date', 'section_6_extension_date', 'further_extension_date', 
                'certificate', 'covid_certificate', 'renewed_certificate', 'further_extension_order', 
                'complaints_litigation', 'project_sub_type', 'latitude', 'longitude', 'total_area', 
                'open_area', 'units','ProjectAddress','ProjectStatus','ProjectStartDate',
                'ProjectEndDate','ProjectCost','ProjectCarpetArea','WaterSource','OtherWaterSource',
                'OpenParking','CoveredParking','LandCost','PlinthArea','ApprovingAuth'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # Write header only if the file is empty
            csvfile.seek(0, os.SEEK_END)  # Move to the end of the file
            if csvfile.tell() == 0:
                writer.writeheader()
                print("CSV header written.")

            for term in search_terms:
                print(f"\nProcessing search term: '{term}'")
                try:
                    # Enter the term in the search bar and press Enter
                    search_bar = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="search"]')))
                    driver.execute_script("arguments[0].scrollIntoView(true);", search_bar)
                    search_bar.clear()
                    search_bar.send_keys(term)
                    search_bar.send_keys(u'\ue007')  # Press Enter key
                    print(f"Entered '{term}' into search bar and pressed Enter.")

                    # Wait for the table to update with search results
                    try:
                        wait.until(EC.presence_of_element_located((By.XPATH, '//table[@id="approvedTable"]')))
                        print("Search results table loaded.")
                    except TimeoutException:
                        print(f"Search results for '{term}' did not load in time.")
                        continue  # Skip to the next term

                    # Extract data from the table
                    rows = driver.find_elements(By.XPATH, '//table[@id="approvedTable"]/tbody/tr')
                    if not rows:
                        print(f"No data found for search term '{term}'.")
                        continue

                    for row in rows:
                        cells = row.find_elements(By.TAG_NAME, 'td')
                        if cells and len(cells) >= 19:
                            table_data = {
                                's_no': cells[0].text.strip(),
                                'ack_no': cells[1].text.strip(),
                                'reg_no': cells[2].text.strip(),
                                'promoter_name': cells[4].text.strip(),
                                'project_name': cells[5].text.strip(),
                                'status': cells[6].text.strip(),
                                'district': cells[7].text.strip(),
                                'taluk': cells[8].text.strip(),
                                'approved_on': cells[9].text.strip(),
                                'proposed_completion_date': cells[10].text.strip(),
                                'covid_extension_date': cells[11].text.strip(),
                                'section_6_extension_date': cells[12].text.strip(),
                                'further_extension_date': cells[13].text.strip(),
                                'certificate': cells[14].text.strip(),
                                'covid_certificate': cells[15].text.strip(),
                                'renewed_certificate': cells[16].text.strip(),
                                'further_extension_order': cells[17].text.strip(),
                                'complaints_litigation': cells[18].text.strip()
                            }

                            # Click the icon to open the details page
                            try:
                                icon = row.find_element(By.XPATH, './/i[@class="fa fa-files-o" and @style="font-size:30px;color:#3948B1"]')
                                driver.execute_script("arguments[0].scrollIntoView(true);", icon)
                                try:
                                    icon.click()
                                    print("Clicked on the details icon.")
                                except ElementClickInterceptedException:
                                    driver.execute_script("arguments[0].click();", icon)
                                    print("Clicked on the details icon using JavaScript.")

                                # Handle potential new window/tab
                                original_window = driver.current_window_handle
                                all_windows = driver.window_handles
                                if len(all_windows) > 1:
                                    for window in all_windows:
                                        if window != original_window:
                                            driver.switch_to.window(window)
                                            print("Switched to the new window/tab for project details.")
                                            break

                                # Use the text content of the tabs to find the correct one
                                try:
                                    project_details_tab = wait.until(EC.element_to_be_clickable(
                                        (By.XPATH, '//a[contains(text(),"Project Details")]')))
                                    driver.execute_script("arguments[0].scrollIntoView(true);", project_details_tab)
                                    project_details_tab.click()
                                    print("Clicked on 'Project Details' tab.")
                                except TimeoutException:
                                    print("Project Details tab not found, skipping this record.")
                                    # Close the new window/tab if opened
                                    if len(driver.window_handles) > 1:
                                        driver.close()
                                        driver.switch_to.window(original_window)
                                    else:
                                        driver.back()
                                    continue  # Skip to the next term

                                # Wait for the new details to load, with a 5-second maximum wait
                                try:
                                    wait_short = WebDriverWait(driver, 5)
                                    wait_short.until(EC.presence_of_all_elements_located(
                                        (By.XPATH, '//div[@class="col-md-3 col-sm-6 col-xs-6"]/p')))
                                    print("Project details loaded.")
                                except TimeoutException:
                                    print("Project details not found within 5 seconds. Skipping this record.")
                                    # Close the new window/tab if opened
                                    if len(driver.window_handles) > 1:
                                        driver.close()
                                        driver.switch_to.window(original_window)
                                    else:
                                        driver.back()
                                    continue  # Skip to the next term

                                # Extract additional details
                                project_details = driver.find_elements(By.XPATH, '//div[@class="col-md-3 col-sm-6 col-xs-6"]/p')
                                taluk_details = driver.find_elements(By.XPATH, '//div[@class="col-md-6 col-sm-6 col-xs-6"]/p')

                                # Initialize all additional fields
                                additional_fields = {
                                    'project_sub_type': '',
                                    'ProjectStatus': '',
                                    'ProjectStartDate': '',
                                    'ProjectEndDate': '',
                                    'ProjectCost': '',
                                    'ProjectCarpetArea': '',
                                    'WaterSource': '',
                                    'OtherWaterSource': '',
                                    'OpenParking': '',
                                    'CoveredParking': '',
                                    'LandCost': '',
                                    'PlinthArea': '',
                                    'ApprovingAuth': '',
                                    'total_area': '',
                                    'open_area': '',
                                    'units': '',
                                    'ProjectAddress': '',
                                    'taluk': '',
                                    'latitude': '',
                                    'longitude': ''
                                }

                                # Combined mapping for all fields
                                mapping = {
                                    'Project Sub Type': 'project_sub_type',
                                    'Project Status': 'ProjectStatus',
                                    'Project Start Date': 'ProjectStartDate',
                                    'Proposed Completion Date': 'ProjectEndDate',
                                    'Total Project Cost (INR)': 'ProjectCost',
                                    'Total Carpet Area of all the Floors (Sq Mtr)': 'ProjectCarpetArea',
                                    'Source of Water': 'WaterSource',
                                    'Others': 'OtherWaterSource',
                                    'No. of Open Parking': 'OpenParking',
                                    'No. of Covered Parking': 'CoveredParking',
                                    'Cost of Land (INR)': 'LandCost',
                                    'Total Plinth Area (Sq Mtr)': 'PlinthArea',
                                    'Approving Authority': 'ApprovingAuth',
                                    'Total Area Of Land (Sq Mtr)': 'total_area',
                                    'Total Open Area (Sq Mtr)': 'open_area',
                                    'Total Number of Inventories/Flats/Sites/Plots/Villas': 'units',
                                    'Taluk': 'taluk',
                                    'Project Address': 'ProjectAddress',
                                    'Latitude': 'latitude',
                                    'Longitude': 'longitude'
                                }

                                # Parse project details
                                for i in range(len(project_details)):
                                    label = project_details[i].text.strip(':').strip()
                                    if i + 1 < len(project_details):
                                        value = project_details[i + 1].text.strip()
                                        key = mapping.get(label)
                                        if key:
                                            additional_fields[key] = value

                                # Parse address details
                                for i in range(len(taluk_details)):
                                    label = taluk_details[i].text.strip(':').strip()
                                    if i + 1 < len(taluk_details):
                                        value = taluk_details[i + 1].text.strip()
                                        key = mapping.get(label)
                                        if key:
                                            additional_fields[key] = value

                                # Update table data with additional details
                                table_data.update(additional_fields)

                                # Print the extracted data for debugging
                                print(f"Extracted Data: {table_data}")

                                # Write the extracted data to the CSV file
                                writer.writerow(table_data)
                                print("Data written to 'new_data.csv'.")

                                # Close the new window/tab if opened and switch back
                                if len(driver.window_handles) > 1:
                                    driver.close()
                                    driver.switch_to.window(original_window)
                                    print("Closed the project details window and switched back to the main window.")
                                else:
                                    driver.back()
                                    print("Navigated back to the main table page.")

                                # Wait for the table to reload before proceeding
                                wait.until(EC.presence_of_element_located((By.XPATH, '//table[@id="approvedTable"]')))
                                print("Main table page reloaded.")

                            except (NoSuchElementException, TimeoutException, ElementClickInterceptedException, UnexpectedAlertPresentException) as e:
                                print(f"Exception while handling icon or details: {e}")
                                # Handle unexpected alerts
                                try:
                                    alert = driver.switch_to.alert
                                    alert.dismiss()
                                    print("Dismissed unexpected alert.")
                                except:
                                    pass
                                # Attempt to navigate back to the main table
                                if len(driver.window_handles) > 1:
                                    driver.close()
                                    driver.switch_to.window(original_window)
                                    print("Closed unexpected window/tab and switched back to the main window.")
                                else:
                                    driver.back()
                                    print("Navigated back to the main table page.")
                                # Wait for the table to reload
                                wait.until(EC.presence_of_element_located((By.XPATH, '//table[@id="approvedTable"]')))
                                continue  # Skip to the next term

                except Exception as e:
                    print(f"Exception while handling search term '{term}': {e}")
                    continue

                finally:
                    # After processing each search term, reload the page to reset the search interface
                    try:
                        print("Reloading the main page to reset the search interface.")
                        driver.get(URL)
                        print("Reloaded the main page.")

                        # Wait for the page to load
                        wait.until(EC.presence_of_element_located((By.ID, 'projectDist')))
                        print("Main page loaded after reload.")

                        # Re-enter 'Bengaluru Urban' and click search
                        search_input = wait.until(EC.element_to_be_clickable((By.ID, 'projectDist')))
                        set_input_value(driver, search_input, 'Bengaluru Urban')
                        print("Re-entered 'Bengaluru Urban' into 'projectDist' via JavaScript after reload.")

                        # Find and click the search button
                        try:
                            search_button = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'btn-style')))
                            print("Found search button after reload.")
                            search_button.click()
                            print("Clicked search button after reload.")
                        except (TimeoutException, ElementClickInterceptedException) as e:
                            print(f"Failed to click search button after reload: {e}")
                            continue

                        # Wait for the table to load again
                        try:
                            wait.until(EC.presence_of_element_located((By.XPATH, '//table[@id="approvedTable"]')))
                            print("Approved projects table loaded after reload.")
                        except TimeoutException:
                            print("Approved projects table did not load in time after reload.")
                            continue

                    except Exception as e:
                        print(f"Failed to reload and reset search interface: {e}")
                        continue

    finally:
        driver.quit()
        print("Browser closed.")

# Call the function with a specified serial number to start processing
process_data_from_serial(1)
