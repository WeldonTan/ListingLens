# listinglens.py
import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementClickInterceptedException,
    StaleElementReferenceException, WebDriverException
)

import pandas as pd
import os
import time
import traceback
import google.generativeai as genai
import logging
import json
import concurrent.futures
from urllib.parse import urlparse

# --- Logging Configuration ---
log_file = 'property_scraper.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Configuration ---
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    if not GOOGLE_API_KEY:
        st.error("Google API Key not found in Streamlit Secrets. Please add it.")
        logger.error("Google API Key not found in Streamlit Secrets.")
        st.stop()
except KeyError:
    st.error("Google API Key not found in Streamlit Secrets. Please configure `GOOGLE_API_KEY` in your app's secrets.")
    logger.error("Google API Key setting is missing in Streamlit Secrets.")
    st.stop()
except Exception as e:
    st.error(f"Error accessing Streamlit Secrets: {e}")
    logger.error(f"Error accessing Streamlit Secrets: {e}", exc_info=True)
    st.stop()

# --- Constants ---
MAX_CONCURRENT_WORKERS = 3 # Reduced for stability

PAGE_LOAD_TIMEOUT = 10.0 # Increased for reliability
BUTTON_WAIT_TIMEOUT = 3.0
POST_CLICK_DELAY = 1.5
POST_EXPANSION_CLICK_DELAY = 1.5
DELAY_BEFORE_POST_EXPANSION_SEARCH = 1.5
SECOND_EXPANSION_CLICK_DELAY = 1.5
POST_SECOND_EXPANSION_CLICK_DELAY = 1.5

COLUMN_ORDER = [
    'url', 'listing_title', 'project_name', 'price', 'area', 'state',
    'sq_ft', 'bedrooms', 'bathrooms',
    'property_type', 'carpark', 'floor_range',
    'phone_number', 'description',
    'processing_time_seconds', 'error'
]

target_css_selectors = [
        "script[id='__NEXT_DATA__']", # Next.js Data - Priority for raw data
        "script[type='application/ld+json']", # JSON-LD Data
        "body" # Fallback: Analyze the entire page content. Robust but token-heavy.
]

# --- Gemini API Initialization ---
try:
    genai.configure(api_key=GOOGLE_API_KEY)
    logger.info("Gemini API configured successfully.")
except Exception as e:
    st.error(f"Failed to configure Gemini API: {e}")
    logger.error(f"Failed to configure Gemini API: {e}", exc_info=True)
    st.stop()

# --- Selenium Options ---
chrome_options = Options()
chrome_options.page_load_strategy = 'eager'
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--log-level=3")
chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
chrome_options.add_argument('--disable-infobars')
chrome_options.add_argument('--disable-extensions')
# chrome_options.binary_location = "/usr/bin/chromium" # For Streamlit Cloud, if needed

# --- Helper Functions ---
def format_elapsed_time(start_time: float) -> str:
    elapsed = time.time() - start_time
    return f"[+{elapsed:.2f}s]"

def click_button(driver, button_element, xpath_description, wait_timeout, post_click_delay, start_time_for_logging, click_attempt_description=""):
    clicked = False
    btn_text = "(unknown)"
    try:
        if button_element and button_element.is_displayed() and button_element.is_enabled():
            button_to_click = WebDriverWait(driver, wait_timeout).until(
                EC.element_to_be_clickable((By.XPATH, xpath_description))
            )
            try:
                button_to_click = driver.find_element(By.XPATH, xpath_description)
                btn_text = button_to_click.text.strip().replace('\n', ' ')[:50]
            except StaleElementReferenceException:
                btn_text = "(stale element)"
                try:
                    time.sleep(0.5)
                    button_to_click = driver.find_element(By.XPATH, xpath_description)
                    btn_text = button_to_click.text.strip().replace('\n', ' ')[:50]
                except Exception:
                     btn_text = "(stale element - retry failed)"
            except Exception:
                btn_text = "(error getting text)"
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button_to_click)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", button_to_click)
                clicked = True
                print(f"{format_elapsed_time(start_time_for_logging)}     {click_attempt_description}Clicked button: '{btn_text}' using XPath: {xpath_description}")
                logger.info(f"{click_attempt_description}Clicked button: '{btn_text}' using XPath: {xpath_description}")
                time.sleep(post_click_delay)
                print(f"{format_elapsed_time(start_time_for_logging)}     Post-click delay ({post_click_delay}s) finished for '{btn_text}'.")
            except StaleElementReferenceException:
                 print(f"{format_elapsed_time(start_time_for_logging)}     StaleElementReferenceException during JS click for XPath: {xpath_description}. Re-finding...")
                 logger.warning(f"StaleElementReferenceException during JS click for XPath: {xpath_description}. Re-finding...")
                 try:
                     time.sleep(0.5)
                     button_fresh = driver.find_element(By.XPATH, xpath_description)
                     driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button_fresh)
                     time.sleep(0.5)
                     driver.execute_script("arguments[0].click();", button_fresh)
                     clicked = True
                     print(f"{format_elapsed_time(start_time_for_logging)}     {click_attempt_description}Clicked button (after re-find): '{btn_text}' using XPath: {xpath_description}")
                     logger.info(f"{click_attempt_description}Clicked button (after re-find): '{btn_text}' using XPath: {xpath_description}")
                     time.sleep(post_click_delay)
                     print(f"{format_elapsed_time(start_time_for_logging)}     Post-click delay ({post_click_delay}s) finished for '{btn_text}'.")
                 except Exception as e_retry_click:
                     print(f"{format_elapsed_time(start_time_for_logging)}     Error clicking button after re-find for XPath '{xpath_description}': {type(e_retry_click).__name__}")
                     logger.error(f"Error clicking button after re-find for XPath '{xpath_description}': {type(e_retry_click).__name__}")
            except Exception as e_js_click:
                 print(f"{format_elapsed_time(start_time_for_logging)}     Error during JS click for XPath '{xpath_description}': {type(e_js_click).__name__}")
                 logger.error(f"Error during JS click for XPath '{xpath_description}': {type(e_js_click).__name__}")
    except TimeoutException:
        print(f"{format_elapsed_time(start_time_for_logging)}     Timeout waiting for button to be clickable (Timeout: {wait_timeout}s) for XPath: {xpath_description}")
        logger.warning(f"Timeout waiting for button to be clickable (Timeout: {wait_timeout}s) for XPath: {xpath_description}")
        pass
    except StaleElementReferenceException:
        print(f"{format_elapsed_time(start_time_for_logging)}     StaleElementReferenceException checking/waiting for button with XPath: {xpath_description}. Page might have updated.")
        logger.warning(f"StaleElementReferenceException checking/waiting for button with XPath: {xpath_description}.")
        pass
    except NoSuchElementException:
        print(f"{format_elapsed_time(start_time_for_logging)}     NoSuchElementException when trying to re-find button for clickability check/JS click: {xpath_description}.")
        logger.warning(f"NoSuchElementException when trying to re-find button for clickability check/JS click: {xpath_description}.")
        pass
    except ElementClickInterceptedException:
        print(f"{format_elapsed_time(start_time_for_logging)}     ElementClickInterceptedException for button with XPath: {xpath_description}. Another element may be blocking.")
        logger.warning(f"ElementClickInterceptedException for button with XPath: {xpath_description}.")
        pass
    except Exception as e_click:
        print(f"{format_elapsed_time(start_time_for_logging)}     Error clicking button instance with XPath '{xpath_description}': {type(e_click).__name__} - {e_click}")
        logger.error(f"Error clicking button instance with XPath '{xpath_description}': {type(e_click).__name__} - {e_click}")
        pass
    return clicked, btn_text

def extract_property_details(html_content, listing_url):
    if not html_content or html_content.isspace():
        logger.warning(f"HTML content provided to Gemini for {listing_url} is empty or whitespace. Skipping AI extraction.")
        return json.dumps({"url": listing_url, "error": "No HTML content extracted from page to analyze."})
    logger.info(f"Attempting to extract details using Gemini for URL: {listing_url}")
    gemini_start_time = time.perf_counter()
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""
        You are an expert property data extractor. Analyze the following HTML content from a property listing website
        (potentially combined from several relevant sections like description, details, contact, and property specifics)
        and extract the following information in a JSON format:

        - listing_title: The full title of the property listing as it appears. Look in <title> tags or main headings (h1, h2). If not found, return "N/A".
        - project_name: The specific building, condo, or project name IF clearly identifiable within the title or description (e.g., "Winner Court A", "Cubic Botanical", "Sky Residences"). If not clear or just a general area name, return "N/A".
        - area: The area/location (e.g., "Desa Petaling", "Bangsar South", "Damansara"). Look for location indicators near the title or in details sections. If not found, return "N/A".
        - state: The state (e.g., "Kuala Lumpur", "Selangor", "Johor"). Look for location indicators. If not found, return "N/A".
        - price: The listed price (for sale) or rent per month (for rent) as a number (integer). Remove currency symbols (like RM), commas, and text like "/ month" or "per month". If not found or cannot be converted to a number, return 0. Prioritize the main listed price.
        - sq_ft: The size in square feet as a number (integer). Remove "sq.ft.", "sf", etc. If not found or cannot be converted, return 0.
        - bedrooms: The number of bedrooms as a number (integer). Look for labels like "Bedrooms", "Beds", or patterns like "3R". If not found or cannot be converted, return 0.
        - bathrooms: The number of bathrooms as a number (integer). Look for labels like "Bathrooms", "Baths", or patterns like "2B". If not found or cannot be converted, return 0.
        - property_type: The type of property (e.g., "Condominium", "Serviced Residence", "Bungalow"). Look for labels like "Property Type". If not found, return "N/A".
        - carpark: The number of car park spaces as a number (integer). Look for labels like "Carpark", "Parking". If not found or cannot be converted, return 0.
        - floor_range: The floor range (e.g., "High", "Mid", "Low", "5-10"). Look for labels like "Floor Range". If not found, return "N/A".
        - phone_number: The complete contact phone number. Look very carefully, it might be within a <p> tag (e.g., <p class="style__BaseText-sc-1m7z3v7-1 efceJJ">0133932356</p>) inside a contact button or other contact block. Extract the full phone number, including country codes if present. Prioritize the complete number over partial numbers. For Malaysia numbers, an example format is +60123456789. If not found, return "N/A".
        - description: A concise summary of the property description. Look for description blocks, meta description tags, or sections labeled 'Description'. Include key details, even those potentially revealed after clicking 'show more' in the original page (which should be in the provided HTML). If not found, return "N/A".

        Return ONLY the data in a valid JSON object format. Do not include ```json markdown wrappers or any text before or after the JSON object itself. Ensure all keys are present, using "N/A" or 0 as specified for missing values.

        Example of the desired JSON output format:
        {{
          "listing_title": "Luxury Condo with KLCC View",
          "project_name": "Sky Residences",
          "area": "Ampang Hilir",
          "state": "Kuala Lumpur",
          "price": 1200000,
          "sq_ft": 1500,
          "bedrooms": 3,
          "bathrooms": 2,
          "property_type": "Condominium",
          "carpark": 2,
          "floor_range": "High",
          "phone_number": "0123456789",
          "description": "Fully furnished 3-bedroom unit at Sky Residences. High floor with stunning KLCC view. Includes 2 car parks. Available now."
        }}

        HTML Content:
        ```html
        {html_content}
        ```
        """
        response = model.generate_content(prompt)
        json_string = response.text.strip().strip('```json').strip('```').strip()
        logger.debug(f"Raw Gemini response for {listing_url}: {json_string[:500]}...")
        try:
            data = json.loads(json_string)
            if isinstance(data, dict):
                 data['url'] = listing_url
                 gemini_duration = time.perf_counter() - gemini_start_time
                 logger.info(f"Gemini extraction successful and parsed for {listing_url} in {gemini_duration:.2f} seconds.")
                 return json.dumps(data)
            else:
                 logger.warning(f"Gemini output for {listing_url} was not a dictionary after parsing: {json_string}")
                 return json.dumps({"url": listing_url, "error": "AI output was not a valid JSON object."})
        except json.JSONDecodeError as json_err:
             logger.error(f"Failed to parse Gemini JSON response for {listing_url}: {json_err}. Response: {json_string}", exc_info=True)
             return json.dumps({"url": listing_url, "error": f"Failed to parse AI response: {json_err}. Raw response: {json_string[:200]}..."})
        except Exception as add_url_err:
             logger.error(f"Error adding URL to Gemini result for {listing_url}: {add_url_err}", exc_info=True)
             return json.dumps({"url": listing_url, "error": f"Internal error processing AI result: {add_url_err}"})
    except Exception as e:
        gemini_duration = time.perf_counter() - gemini_start_time
        logger.error(f"Gemini extraction failed for {listing_url} after {gemini_duration:.2f} seconds: {e}", exc_info=True)
        error_msg = f"Gemini API call failed: {str(e)}".replace('"', "'")
        return json.dumps({"url": listing_url, "error": error_msg})

def scrape_targeted_sections(url: str, target_selectors: list[str]):
    logger.info(f"Processing URL: {url}")
    print(f"Processing URL: {url}")
    driver = None
    start_time = time.time()
    result = {"url": url, "extracted_data": {selector: [] for selector in target_selectors}, "error": None, "raw_error": None}

    # XPaths for buttons to click, using case-insensitive matching
    initial_button_xpaths = [
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'view number')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show more')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'reveal phone')]",
        "//button[contains(text(),'01')]", # Specific for Mudah.my style buttons
        "//button[@aria-label='Show phone number']", # Metadata based selector
        "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show more')]",
        "//span[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'view number')]",
        "//div[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'view number')]",
        "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'click to show')]",
    ]
    expansion_button_texts = ["show more", "read more", "view more"]
    post_expansion_contact_xpaths = [
         "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show contact number')]",
         "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show contact number')]",
         "//div[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show contact number')]",
    ]

    try:
        print(f"{format_elapsed_time(start_time)} Initializing WebDriver...")
        # For Streamlit Cloud, you might need to specify the service path
        # service = Service(executable_path="/usr/bin/chromedriver")
        # driver = webdriver.Chrome(service=service, options=chrome_options)
        driver = webdriver.Chrome(options=chrome_options) # Local testing
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        print(f"{format_elapsed_time(start_time)} WebDriver initialized.")

        print(f"{format_elapsed_time(start_time)} Loading page (Timeout: {PAGE_LOAD_TIMEOUT}s)...")
        driver.get(url)
        WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        )
        print(f"{format_elapsed_time(start_time)} Page loaded.")
        initial_settle_delay = 2.0
        print(f"{format_elapsed_time(start_time)} Allowing {initial_settle_delay}s for initial elements to settle...")
        time.sleep(initial_settle_delay)
        print(f"{format_elapsed_time(start_time)} Post-load delay finished.")

        print(f"{format_elapsed_time(start_time)} Attempting to click initial reveal/expansion buttons...")
        initial_click_attempts = 0
        clicked_initial_button_texts = []
        expansion_buttons_clicked = []
        for xpath in initial_button_xpaths:
            is_expansion_xpath = any(txt in xpath.lower() for txt in expansion_button_texts)
            try:
                potential_buttons = WebDriverWait(driver, BUTTON_WAIT_TIMEOUT).until(
                    EC.presence_of_all_elements_located((By.XPATH, xpath))
                )
                if not potential_buttons: continue
                for i, button in enumerate(potential_buttons):
                    if not isinstance(button, webdriver.remote.webelement.WebElement):
                         print(f"{format_elapsed_time(start_time)}     Skipping invalid element found for XPath '{xpath}' at index {i}.")
                         continue
                    specific_xpath = f"({xpath})[{i+1}]"
                    try:
                        clicked, btn_text = click_button(driver, button, specific_xpath, BUTTON_WAIT_TIMEOUT, POST_CLICK_DELAY, start_time, click_attempt_description="(Attempt 1) ")
                        if clicked:
                            initial_click_attempts += 1
                            clicked_initial_button_texts.append(f"'{btn_text}...'")
                            if is_expansion_xpath:
                                expansion_buttons_clicked.append(specific_xpath)
                    except Exception as e_inner_click:
                         print(f"{format_elapsed_time(start_time)}     Error processing button {i+1} for XPath '{xpath}': {type(e_inner_click).__name__}")
                         logger.error(f"Error processing button {i+1} for XPath '{xpath}': {type(e_inner_click).__name__}")
            except TimeoutException:
                 print(f"{format_elapsed_time(start_time)}   Timeout waiting for initial buttons for XPath '{xpath}' (Wait: {BUTTON_WAIT_TIMEOUT}s).")
                 logger.warning(f"Timeout waiting for initial buttons for XPath '{xpath}' (Wait: {BUTTON_WAIT_TIMEOUT}s).")
            except StaleElementReferenceException:
                 print(f"{format_elapsed_time(start_time)}   StaleElementReferenceException while finding initial buttons for XPath '{xpath}'. Skipping rest for this XPath.")
                 logger.warning(f"StaleElementReferenceException while finding initial buttons for XPath '{xpath}'.")
            except Exception as e_find:
                 print(f"{format_elapsed_time(start_time)}   Error finding/processing elements with initial XPath '{xpath}': {type(e_find).__name__} - {e_find}")
                 logger.error(f"Error finding/processing elements with initial XPath '{xpath}': {type(e_find).__name__} - {e_find}")

        if expansion_buttons_clicked:
            print(f"{format_elapsed_time(start_time)} Pausing {SECOND_EXPANSION_CLICK_DELAY}s before attempting second click...")
            time.sleep(SECOND_EXPANSION_CLICK_DELAY)
            print(f"{format_elapsed_time(start_time)} Attempting second click on {len(expansion_buttons_clicked)} expansion button(s)...")
            second_click_success_count = 0
            for specific_xpath in expansion_buttons_clicked:
                try:
                    button_element_for_second_click = WebDriverWait(driver, BUTTON_WAIT_TIMEOUT).until(
                        EC.presence_of_element_located((By.XPATH, specific_xpath))
                    )
                    clicked, btn_text = click_button(driver, button_element_for_second_click, specific_xpath, BUTTON_WAIT_TIMEOUT, POST_SECOND_EXPANSION_CLICK_DELAY, start_time, click_attempt_description="(Attempt 2) ")
                    if clicked:
                        second_click_success_count += 1
                        print(f"{format_elapsed_time(start_time)}     Successfully performed second click on: '{btn_text}'")
                        logger.info(f"Successfully performed second click on: '{btn_text}' XPath: {specific_xpath}")
                except TimeoutException:
                    print(f"{format_elapsed_time(start_time)}     Expansion button timed out before second click (Wait: {BUTTON_WAIT_TIMEOUT}s): {specific_xpath}")
                    logger.warning(f"Expansion button timed out before second click (Wait: {BUTTON_WAIT_TIMEOUT}s): {specific_xpath}")
                except NoSuchElementException:
                    print(f"{format_elapsed_time(start_time)}     Could not re-find expansion button for second click: {specific_xpath}")
                    logger.warning(f"Could not re-find expansion button for second click: {specific_xpath}")
                except Exception as e_second_click:
                    print(f"{format_elapsed_time(start_time)}     Error during second click attempt for XPath '{specific_xpath}': {type(e_second_click).__name__}")
                    logger.error(f"Error during second click attempt for XPath '{specific_xpath}': {type(e_second_click).__name__}")
            if second_click_success_count > 0:
                 print(f"{format_elapsed_time(start_time)} Second click attempted successfully on {second_click_success_count} expansion button(s).")

        if initial_click_attempts > 0:
            print(f"{format_elapsed_time(start_time)} Initial click phase completed. Clicked: {', '.join(clicked_initial_button_texts)}")
        else:
            print(f"{format_elapsed_time(start_time)} No initial reveal/expansion buttons found or clicked.")

        print(f"{format_elapsed_time(start_time)} Pausing {DELAY_BEFORE_POST_EXPANSION_SEARCH}s before post-expansion search...")
        time.sleep(DELAY_BEFORE_POST_EXPANSION_SEARCH)
        print(f"{format_elapsed_time(start_time)} Pause finished.")

        print(f"{format_elapsed_time(start_time)} Attempting to click post-expansion contact buttons...")
        post_expansion_clicks = 0
        clicked_post_expansion_texts = []
        for xpath in post_expansion_contact_xpaths:
             try:
                potential_buttons = WebDriverWait(driver, BUTTON_WAIT_TIMEOUT).until(
                    EC.presence_of_all_elements_located((By.XPATH, xpath))
                )
                if not potential_buttons: continue
                for i, button in enumerate(potential_buttons):
                    if not isinstance(button, webdriver.remote.webelement.WebElement):
                         print(f"{format_elapsed_time(start_time)}     Skipping invalid post-expansion element found for XPath '{xpath}' at index {i}.")
                         continue
                    specific_xpath = f"({xpath})[{i+1}]"
                    try:
                        clicked, btn_text = click_button(driver, button, specific_xpath, BUTTON_WAIT_TIMEOUT, POST_EXPANSION_CLICK_DELAY, start_time)
                        if clicked:
                             post_expansion_clicks += 1
                             clicked_post_expansion_texts.append(f"'{btn_text}...'")
                    except Exception as e_inner_click:
                         print(f"{format_elapsed_time(start_time)}     Error processing post-expansion button {i+1} for XPath '{xpath}': {type(e_inner_click).__name__}")
                         logger.error(f"Error processing post-expansion button {i+1} for XPath '{xpath}': {type(e_inner_click).__name__}")
             except TimeoutException:
                 print(f"{format_elapsed_time(start_time)}   Timeout waiting for post-expansion buttons for XPath '{xpath}' (Wait: {BUTTON_WAIT_TIMEOUT}s).")
                 logger.warning(f"Timeout waiting for post-expansion buttons for XPath '{xpath}' (Wait: {BUTTON_WAIT_TIMEOUT}s).")
             except StaleElementReferenceException:
                 print(f"{format_elapsed_time(start_time)}   StaleElementReferenceException while finding post-expansion buttons for XPath '{xpath}'.")
                 logger.warning(f"StaleElementReferenceException while finding post-expansion buttons for XPath '{xpath}'.")
             except Exception as e_find:
                 print(f"{format_elapsed_time(start_time)}   Error finding/processing elements with post-expansion XPath '{xpath}': {type(e_find).__name__} - {e_find}")
                 logger.error(f"Error finding/processing elements with post-expansion XPath '{xpath}': {type(e_find).__name__} - {e_find}")

        if post_expansion_clicks > 0:
            print(f"{format_elapsed_time(start_time)} Clicked {post_expansion_clicks} post-expansion button(s): {', '.join(clicked_post_expansion_texts)}")
        else:
            print(f"{format_elapsed_time(start_time)} No post-expansion contact buttons found or clicked.")

        print(f"{format_elapsed_time(start_time)} Extracting content from target selectors...")
        if not target_selectors:
             print(f"{format_elapsed_time(start_time)} Warning: No target selectors provided.")
             logger.warning(f"No target CSS selectors provided for URL: {url}")
        extraction_start_time = time.time()
        extracted_html_dict = result["extracted_data"]
        extraction_wait_timeout = 1.5
        for i, selector in enumerate(target_selectors):
            selector_start_time = time.time()
            try:
                WebDriverWait(driver, extraction_wait_timeout).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                )
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(f"{format_elapsed_time(start_time)}   Found {len(elements)} element(s) for selector: '{selector}' (took {time.time() - selector_start_time:.2f}s)")
                    for element_index, element in enumerate(elements):
                        try:
                            if element.is_displayed():
                                outer_html = element.get_attribute('outerHTML')
                                if outer_html:
                                    extracted_html_dict[selector].append(outer_html.strip())
                        except StaleElementReferenceException:
                             print(f"{format_elapsed_time(start_time)}     Stale element {element_index+1} encountered getting HTML for selector '{selector}'. Skipping.")
                             logger.warning(f"Stale element {element_index+1} encountered for selector '{selector}'.")
                        except Exception as e_html:
                             print(f"{format_elapsed_time(start_time)}     Error getting HTML for element {element_index+1} selector '{selector}': {type(e_html).__name__}")
                             logger.error(f"Error getting HTML for element {element_index+1} selector '{selector}': {type(e_html).__name__}")
            except TimeoutException:
                 print(f"{format_elapsed_time(start_time)}   Timeout waiting {extraction_wait_timeout}s for elements for selector: '{selector}' (after {time.time() - selector_start_time:.2f}s)")
                 logger.warning(f"Timeout waiting {extraction_wait_timeout}s for elements for selector: '{selector}'")
            except Exception as e:
                print(f"{format_elapsed_time(start_time)}   Error finding elements for selector '{selector}': {type(e).__name__} - {e} (after {time.time() - selector_start_time:.2f}s)")
                logger.error(f"Error finding elements for selector '{selector}': {type(e).__name__} - {e}")
        print(f"{format_elapsed_time(start_time)} Finished extraction phase (took {time.time() - extraction_start_time:.2f}s)")
        if not any(extracted_html_dict.values()):
            print(f"{format_elapsed_time(start_time)} Warning: No HTML content was extracted from any target selectors.")
            logger.warning(f"No HTML content extracted for any target selector for URL: {url}")

    except WebDriverException as e:
        raw_err_msg = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        if "net::ERR_CONNECTION_REFUSED" in str(e) or "unable to connect to renderer" in str(e) or "DevToolsActivePort file doesn't exist" in str(e):
            err_msg = f"WebDriver Error (Cloud Env): Potential issue connecting to the browser instance. Check `packages.txt` & resources. Details: {type(e).__name__}"
        else:
            err_msg = f"WebDriver Error: {type(e).__name__} - Check Selenium setup/options. Error: {e}"
        print(f"{format_elapsed_time(start_time)} ERROR: {err_msg}")
        logger.error(f"WebDriver error during scraping for {url}: {err_msg}", exc_info=True)
        result["error"] = f"WebDriver setup/runtime error: {type(e).__name__}"
        result["raw_error"] = raw_err_msg
    except TimeoutException as e:
        raw_err_msg = f"Message: {getattr(e, 'msg', 'N/A')}\nStacktrace:\n{getattr(e, 'stacktrace', 'N/A')}"
        err_msg = f"Timeout occurred during page load or element wait (Check PAGE_LOAD_TIMEOUT: {PAGE_LOAD_TIMEOUT}s or other waits). Details: {e.msg}"
        print(f"{format_elapsed_time(start_time)} ERROR: {err_msg}")
        logger.error(f"Timeout error during scraping for {url}: {err_msg}\nRaw Error: {raw_err_msg}", exc_info=False)
        result["error"] = err_msg
        result["raw_error"] = raw_err_msg
    except Exception as e:
        raw_err_msg = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        err_msg = f"An unexpected error occurred during scraping: {type(e).__name__} - {e}"
        print(f"{format_elapsed_time(start_time)} ERROR: {err_msg}")
        logger.error(f"Unexpected error during scraping for {url}: {err_msg}", exc_info=True)
        result["error"] = f"Unexpected scraping error: {type(e).__name__}"
        result["raw_error"] = raw_err_msg
    finally:
        if driver:
            print(f"{format_elapsed_time(start_time)} Closing WebDriver...")
            try:
                driver.quit()
                print(f"{format_elapsed_time(start_time)} WebDriver closed.")
            except Exception as quit_err:
                 print(f"{format_elapsed_time(start_time)} Error quitting WebDriver: {quit_err}")
                 logger.error(f"Error quitting WebDriver for {url}: {quit_err}", exc_info=True)

    total_time = time.time() - start_time
    print(f"Finished processing {url} in {total_time:.2f} seconds.")
    logger.info(f"Finished scraping {url} in {total_time:.2f} seconds. Error: {result['error']}")
    return result

def process_url(url):
    process_start_time = time.perf_counter()
    logger.info(f"Processing URL: {url}")
    result_dict = {"url": url}

    scrape_result = scrape_targeted_sections(url, target_css_selectors)

    scraper_error = scrape_result.get("error")
    if scraper_error:
        logger.error(f"Scraping failed for {url}: {scraper_error}")
        result_dict["error"] = f"Scraping failed: {scraper_error}"
    else:
        extracted_data = scrape_result.get("extracted_data", {})
        all_html_parts = []
        for selector, html_list in extracted_data.items():
            if html_list:
                all_html_parts.extend(html_list)

        if not all_html_parts:
            logger.warning(f"No HTML content was extracted by selectors for {url}. Cannot proceed with AI analysis.")
            result_dict["error"] = "No relevant HTML content found on page by selectors."
        else:
            combined_html = "\n\n".join(all_html_parts)
            logger.info(f"Scraping completed for {url}, combined HTML length: {len(combined_html)}. Proceeding to AI extraction.")
            # print(f"--- DEBUG: Combined HTML for {url} (first 1000 chars) ---\n{combined_html[:1000]}\n--- END DEBUG ---")

            json_data_string = extract_property_details(combined_html, url)

            if json_data_string:
                logger.info(f"Received AI response for {url}.")
                try:
                    data_dict = json.loads(json_data_string)
                    if isinstance(data_dict, dict):
                        result_dict.update(data_dict)
                        ai_error = result_dict.get("error")
                        if ai_error:
                            logger.error(f"AI extraction error for {url}: {ai_error}")
                        else:
                            if "error" in result_dict and not result_dict["error"]:
                                del result_dict["error"]
                            logger.info(f"Successfully extracted data for {url}.")
                    else:
                        logger.error(f"Parsed JSON from AI is not a dictionary for {url}: {data_dict}")
                        result_dict["error"] = "AI response was not in the expected dictionary format."
                except json.JSONDecodeError as e:
                    logger.error(f"JSONDecodeError processing AI response for {url}: {e}. Raw response: {json_data_string[:500]}...", exc_info=True)
                    result_dict["error"] = f"Failed to parse AI response: {e}"
                except Exception as e:
                    logger.error(f"Unexpected error processing AI result for {url}: {e}", exc_info=True)
                    result_dict["error"] = f"Internal processing error after AI: {e}"
            else:
                logger.error(f"No response string received from AI extraction function for {url}.")
                result_dict["error"] = "Failed to get response from AI service function."

    process_end_time = time.perf_counter()
    duration = process_end_time - process_start_time
    result_dict["processing_time_seconds"] = round(duration, 2)
    logger.info(f"Finished processing {url} in {duration:.2f} seconds.")

    if "error" not in result_dict and not all(k in result_dict for k in ['listing_title', 'price']):
         if not scraper_error and not all_html_parts:
             result_dict["error"] = "Processing completed but key data might be missing (No HTML found)."
         elif not scraper_error:
             result_dict["error"] = "Processing completed but key data might be missing (AI extraction likely failed)."

    return result_dict

# --- Streamlit App ---
st.set_page_config(
    page_title="ListingLens - Intelligent Property Scraper",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for a modern look
st.markdown("""
    <style>
    /* Global Styles */
    .main {
        background-color: #f8f9fa;
    }
    .stApp {
        font-family: 'Inter', sans-serif;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #1e293b;
        font-weight: 700;
    }
    
    /* Input Area */
    .stTextArea textarea {
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    }
    .stTextArea textarea:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }
    
    /* Buttons */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        border: none;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transition: all 0.2s;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    }
    
    /* Cards/Containers */
    div[data-testid="stVerticalBlock"] > div {
        /* Minimal styling for containers if needed */
    }
    
    /* Status & Metrics */
    div[data-testid="stMetricValue"] {
        font-size: 1.5rem;
        color: #3b82f6;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #fff;
        border-right: 1px solid #f1f5f9;
    }
    
    /* Hide Streamlit Branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("🏢 ListingLens")
    st.markdown("---")
    st.markdown("### ⚙️ Configuration")
    st.info(f"Running with **{MAX_CONCURRENT_WORKERS}** concurrent workers")
    
    st.markdown("### 📝 Instructions")
    st.markdown("""
    1. Paste **Mudah.my** listing URLs in the main input area.
    2. Ensure each URL is on a new line.
    3. Click **Start Extraction**.
    4. View results in the dashboard and download as CSV.
    """)
    
    st.markdown("---")
    st.caption("Developed by Aelion Systems")

# Main Content
st.title("Property Listing Intelligence")
st.markdown("Transform raw property listings (Mudah.my only) into structured, actionable data using AI.")

# Input Section
with st.container():
    col1, col2 = st.columns([3, 1])
    with col1:
        urls_input = st.text_area(
            "Target URLs",
            height=200,
            placeholder="https://example.com/listing/1\nhttps://example.com/listing/2",
            help="Enter one URL per line"
        )
    with col2:
        st.markdown("#### Actions")
        start_btn = st.button("🚀 Start Extraction", type="primary", use_container_width=True)
        if st.button("🗑️ Clear Results", use_container_width=True):
            st.rerun()

if start_btn:
    if not urls_input.strip():
        st.warning("⚠️ Please enter at least one URL.")
    else:
        batch_start_time = time.perf_counter()
        raw_urls = [url.strip() for url in urls_input.splitlines() if url.strip()]
        
        # Validation
        valid_urls = []
        invalid_inputs = []
        for url in raw_urls:
            try:
                result = urlparse(url)
                if all([result.scheme in ['http', 'https'], result.netloc]):
                    valid_urls.append(url)
                else:
                    invalid_inputs.append(url)
            except:
                invalid_inputs.append(url)
        
        if invalid_inputs:
            st.warning(f"⚠️ {len(invalid_inputs)} invalid URLs ignored.")
            
        if not valid_urls:
            st.error("❌ No valid URLs found.")
        else:
            # Dashboard Area
            st.divider()
            st.subheader("🔄 Extraction Progress")
            
            progress_container = st.container()
            with progress_container:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Metrics placeholders
                m1, m2, m3 = st.columns(3)
                m1.metric("Total URLs", len(valid_urls))
                metric_processed = m2.empty()
                metric_processed.metric("Processed", "0")
                metric_time = m3.empty()
                metric_time.metric("Time Elapsed", "0s")

            all_results = []
            processed_count = 0
            
            # Processing Logic
            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENT_WORKERS) as executor:
                future_to_url = {executor.submit(process_url, url): url for url in valid_urls}
                
                for future in concurrent.futures.as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        result = future.result()
                        all_results.append(result)
                    except Exception as exc:
                        logger.error(f"Error processing {url}: {exc}")
                        all_results.append({"url": url, "error": str(exc)})
                    finally:
                        processed_count += 1
                        progress = processed_count / len(valid_urls)
                        progress_bar.progress(progress)
                        status_text.caption(f"Processing: {url}")
                        metric_processed.metric("Processed", f"{processed_count}/{len(valid_urls)}")
                        elapsed = time.perf_counter() - batch_start_time
                        metric_time.metric("Time Elapsed", f"{elapsed:.1f}s")

            # Results Display
            st.divider()
            total_duration = time.perf_counter() - batch_start_time
            status_text.empty()
            progress_bar.progress(1.0)
            st.success(f"✨ Extraction complete in {total_duration:.2f}s")
            
            successful = [r for r in all_results if not r.get("error")]
            failed = [r for r in all_results if r.get("error")]
            
            tab1, tab2 = st.tabs([f"✅ Successful ({len(successful)})", f"❌ Failed ({len(failed)})"])
            
            with tab1:
                if successful:
                    df = pd.DataFrame(successful)
                    # Reorder columns logic
                    cols = []
                    for c in COLUMN_ORDER:
                        if c in df.columns and c != 'error':
                             cols.append(c)
                    # Add any extra columns found
                    for c in df.columns:
                        if c not in cols and c != 'error':
                            cols.append(c)
                            
                    st.dataframe(df[cols], use_container_width=True)
                    
                    csv = df[cols].to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "📥 Download CSV",
                        data=csv,
                        file_name="listing_data_successful.csv",
                        mime="text/csv",
                        type="primary"
                    )
                else:
                    st.info("No successful extractions.")
                    
            with tab2:
                if failed:
                    st.error(f"{len(failed)} URLs failed to process.")
                    df_failed = pd.DataFrame(failed)
                    st.dataframe(df_failed, use_container_width=True)
                else:
                    st.success("No failures! 🎉")
