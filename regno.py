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
)
from selenium.webdriver.chrome.options import Options


def set_input_value(driver, element, value):
    """
    Sets the value of an input field using JavaScript to bypass potential restrictions.
    """
    driver.execute_script("arguments[0].value = arguments[1];", element, value)
    # Trigger input change events
    driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", element)
    driver.execute_script("arguments[0].dispatchEvent(new Event('input'));", element)


def read_saved_registration_numbers(file_path):
    """
    Reads saved registration numbers from the CSV file.
    Returns a set of registration numbers for quick lookup.
    """
    if not os.path.exists(file_path):
        return set()  # If the file doesn't exist, return an empty set

    with open(file_path, "r", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile)
        next(reader, None)  # Skip the header row
        return set(row[0] for row in reader if row)


def save_registration_numbers_to_csv(file_path, registration_numbers):
    """
    Appends new registration numbers to the CSV file.
    """
    with open(file_path, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        for reg_no in registration_numbers:
            writer.writerow([reg_no])


def extract_registration_numbers():
    # Set Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--headless")  # Optional: Run Chrome in headless mode

    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 20)

    # File path for saving registration numbers
    csv_file_path = "registration_numbers.csv"

    # Read previously saved registration numbers
    saved_registration_numbers = read_saved_registration_numbers(csv_file_path)
    print(f"Loaded {len(saved_registration_numbers)} saved registration numbers.")

    try:
        # Navigate to the website
        URL = "https://rera.karnataka.gov.in/viewAllProjects"
        driver.get(URL)
        print("Navigated to the main URL.")

        # Perform the initial setup
        try:
            district_input = wait.until(EC.element_to_be_clickable((By.ID, "projectDist")))
            print("Found 'District' input field.")
            set_input_value(driver, district_input, "Bengaluru Rural")
            print("Set district to 'Bengaluru Rural'.")

            search_button = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "btn-style")))
            search_button.click()
            print("Clicked the search button.")
        except TimeoutException as e:
            print(f"Failed to set district or click search: {e}")
            return

        # Wait for the "Approved" table to load
        try:
            wait.until(EC.presence_of_element_located((By.ID, "approvedTable")))
            print("Approved projects table loaded.")
        except TimeoutException:
            print("Table did not load in time. Exiting.")
            return

        # Loop through all pages to extract registration numbers
        while True:
            try:
                # Collect rows from the table
                rows = driver.find_elements(By.XPATH, "//table[@id='approvedTable']/tbody/tr")
                if not rows:
                    print("No rows found on this page. Exiting pagination.")
                    break

                new_registration_numbers = set()

                for row in rows:
                    try:
                        reg_no = row.find_element(By.XPATH, "./td[3]").text.strip()  # Assuming column 3 has the registration number
                        if reg_no not in saved_registration_numbers:
                            new_registration_numbers.add(reg_no)
                            print(f"Extracted New Registration Number: {reg_no}")
                        else:
                            print(f"Duplicate Registration Number Skipped: {reg_no}")
                    except NoSuchElementException:
                        print("Could not find registration number in a row. Skipping.")

                # Save new registration numbers to CSV immediately after processing the page
                if new_registration_numbers:
                    save_registration_numbers_to_csv(csv_file_path, new_registration_numbers)
                    saved_registration_numbers.update(new_registration_numbers)  # Update the saved set
                    print(f"Saved {len(new_registration_numbers)} new registration numbers to '{csv_file_path}'.")

                # Check if the 'Next' button exists and is clickable
                try:
                    next_button = driver.find_element(By.XPATH, "//a[@id='approvedTable_next']")
                    if "disabled" in next_button.get_attribute("class"):
                        print("Reached the last page.")
                        break
                    else:
                        next_button.click()
                        print("Navigated to the next page.")
                        time.sleep(2)  # Allow time for the next page to load
                except NoSuchElementException:
                    print("'Next' button not found or disabled. Assuming last page.")
                    break

            except Exception as e:
                print(f"Error during data extraction: {e}")
                break

    finally:
        driver.quit()
        print("Browser closed.")


# Call the function
extract_registration_numbers()