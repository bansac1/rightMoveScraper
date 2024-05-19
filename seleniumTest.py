from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import json
import pandas as pd
import time

url = 'https://www.rightmove.co.uk/property-to-rent/find.html?locationIdentifier=USERDEFINEDAREA%5E%7B%22id%22%3A9827833%7D&maxBedrooms=2&minBedrooms=2&maxPrice=2000&minPrice=2000&propertyTypes=&includeLetAgreed=false&mustHave=&dontShow=&furnishTypes=&keywords='

# Set up the ChromeDriver path
driver_path = "/Users/sachabanks/Downloads/chromedriver-mac-arm64/chromedriver"
service = Service(driver_path)

# Create a WebDriver instance
driver = webdriver.Chrome(service=service)

# Open the webpage
driver.get(url)

# Function to handle cookies pop-up
def handle_cookies(driver):
    try:
        # Wait for the cookies pop-up and accept it if present
        accept_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, 'onetrust-accept-btn-handler'))
        )
        accept_button.click()
        print("Cookies pop-up handled.")
    except Exception as e:
        print("No cookies pop-up found or an error occurred: ", e)

# Function to scroll to the bottom of the page to load all content
def scroll_to_bottom(driver):
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # Wait for new data to load
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

# Function to extract property data from the current page
def extract_properties(driver):
    # Scroll to the bottom of the page to ensure all content is loaded
    scroll_to_bottom(driver)

    # Extract the HTML content
    html_content = driver.page_source
    
    # Parse the HTML with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find the script tag that contains the JSON data
    script_tag = soup.find('script', text=lambda t: t and 'window.jsonModel' in t)
    
    # Extract the JSON data from the script tag
    json_text = script_tag.string.split('window.jsonModel = ')[1].rsplit(';', 1)[0]
    
    # Debugging print
    print("Extracted JSON text length:", len(json_text))
    
    # Ensure the JSON string is properly closed
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as e:
        print("JSONDecodeError:", e)
        print("Problematic JSON text snippet:", json_text[:1000])  # Print the first 1000 characters for debugging
        raise e
    
    return data['properties']

# Handle cookies pop-up if present
handle_cookies(driver)

# Initialize lists to store the extracted data
all_properties = []

# Extract data from the first page
all_properties.extend(extract_properties(driver))

# Function to check if there are more pages
def has_next_page(driver):
    try:
        # Locate the next button using a more specific selector
        next_button = driver.find_element(By.CSS_SELECTOR, 'button.pagination-button.pagination-direction.pagination-direction--next')
        is_enabled = next_button.is_enabled()
        print(f"Next button enabled: {is_enabled}")
        return is_enabled
    except Exception as e:
        print(f"Error checking next button: {e}")
        return False

# Loop through the remaining pages
while has_next_page(driver):
    try:
        # Find the "Next" button and click it
        next_button = driver.find_element(By.CSS_SELECTOR, 'button.pagination-button.pagination-direction.pagination-direction--next')
        next_button.click()
        
        # Wait for the next page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'l-searchResults'))
        )
        
        # Extract data from the new page
        all_properties.extend(extract_properties(driver))
        
        # Pause briefly to avoid overwhelming the server
        time.sleep(2)
    except Exception as e:
        # If there's an error, print it and break out of the loop
        print("An error occurred while navigating pages:", e)
        break

# Close the Selenium driver
driver.quit()

# Extract desired fields from all properties
ids = []
bedrooms = []
bathrooms = []
summaries = []
addresses = []
prices = []
latitudes = []
longitudes = []
images = []

for property in all_properties:
    ids.append(property['id'])
    bedrooms.append(property['bedrooms'])
    bathrooms.append(property['bathrooms'])
    summaries.append(property['summary'])
    addresses.append(property['displayAddress'])
    prices.append(property['price']['displayPrices'][0]['displayPrice'])
    latitudes.append(property['location']['latitude'])
    longitudes.append(property['location']['longitude'])
    images.append(property['propertyImages']['mainImageSrc'])

# Create a DataFrame with the extracted data
properties_df = pd.DataFrame({
    'ID': ids,
    'Bedrooms': bedrooms,
    'Bathrooms': bathrooms,
    'Summary': summaries,
    'Address': addresses,
    'Price': prices,
    'Latitude': latitudes,
    'Longitude': longitudes,
    'MainImage': images
})

# Display the DataFrame
print(properties_df.head())

# Save the data to a CSV file
#properties_df.to_csv('rightmove_properties.csv', index=False)
