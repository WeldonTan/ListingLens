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
MAX_CONCURRENT_WORKERS = 10

PAGE_LOAD_TIMEOUT = 15
BUTTON_WAIT_TIMEOUT = 2
POST_CLICK_DELAY = 1
POST_EXPANSION_CLICK_DELAY = 1
DELAY_BEFORE_POST_EXPANSION_SEARCH = 1
SECOND_EXPANSION_CLICK_DELAY = 1
POST_SECOND_EXPANSION_CLICK_DELAY = 1

COLUMN_ORDER = [
    'url', 'listing_title', 'project_name', 'price', 'area', 'state',
    'sq_ft', 'bedrooms', 'bathrooms', 'phone_number', 'description',
    'processing_time_seconds', 'error'
]

target_css_selectors = [
        "div.Wrapper-ucve63-0.eKOxHS", # Contact Owner block
        "div.style__ParentWrapper-iwjn3z-0.QvHGM", # Listing Details block
        "div.Wrapper-ucve63-0.fKaMDx" # Description block
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
chrome_options.binary_location = "/usr/bin/chromium"

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
        model = genai.GenerativeModel('gemini-2.0-flash')
        prompt = f"""
        You are an expert property data extractor. Analyze the following HTML content from a property listing website
        (potentially combined from several relevant sections like description, details, contact)
        and extract the following information in a JSON format:

        - listing_title: The full title of the property listing as it appears. Look in <title> tags or main headings (h1, h2). If not found, return "N/A".
        - project_name: The specific building, condo, or project name IF clearly identifiable within the title or description (e.g., "Winner Court A", "Cubic Botanical", "Sky Residences"). If not clear or just a general area name, return "N/A".
        - area: The area/location (e.g., "Desa Petaling", "Bangsar South", "Damansara"). Look for location indicators near the title or in details sections. If not found, return "N/A".
        - state: The state (e.g., "Kuala Lumpur", "Selangor", "Johor"). Look for location indicators. If not found, return "N/A".
        - price: The listed price (for sale) or rent per month (for rent) as a number (integer). Remove currency symbols (like RM), commas, and text like "/ month" or "per month". If not found or cannot be converted to a number, return 0. Prioritize the main listed price.
        - sq_ft: The size in square feet as a number (integer). Remove "sq.ft.", "sf", etc. If not found or cannot be converted, return 0.
        - bedrooms: The number of bedrooms as a number (integer). Look for labels like "Bedrooms", "Beds", or patterns like "3R". If not found or cannot be converted, return 0.
        - bathrooms: The number of bathrooms as a number (integer). Look for labels like "Bathrooms", "Baths", or patterns like "2B". If not found or cannot be converted, return 0.
        - phone_number: The contact phone number. Look carefully, it might have been revealed after a button click in the original HTML (and thus present in the provided HTML, potentially multiple times). Extract the first clear phone number found (digits, possibly with +, -, or spaces). If not found, return "N/A".
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

    initial_button_xpaths = [
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'view number')]",
        "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show more')]",
        "//span[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'view number')]",
    ]
    expansion_button_texts = ["show more"]
    post_expansion_contact_xpaths = [
         "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show contact number')]",
         "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show contact number')]"
    ]

    try:
        print(f"{format_elapsed_time(start_time)} Initializing WebDriver for Streamlit Cloud...")
        service = Service(executable_path="/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=chrome_options)
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
        extraction_wait_timeout = 10
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
st.set_page_config(page_title="ListingLens - Property Extractor", layout="wide")

app_style = """
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #ffffff;
            color: #333333;
        }
        .main > div {
            padding-top: 2rem;
            padding-bottom: 2rem;
            padding-left: 1.5rem;
            padding-right: 1.5rem;
        }
        h1 {
            color: #2c3e50;
            text-align: center;
            margin-bottom: 1rem;
        }
        h2, h3, h4, h5, h6 {
             color: #4682B4;
        }
        .stMarkdown p {
            color: #555555;
            line-height: 1.6;
        }
        .stTextArea textarea {
            border: 1px solid #cccccc;
            border-radius: 5px;
            background-color: #f9f9f9;
            font-size: 1rem;
        }
        .stTextArea label {
            color: #4682B4;
            font-weight: 500;
        }
        .stButton>button {
            border-radius: 5px;
            padding: 0.6rem 1.2rem;
            font-weight: 600;
            transition: background-color 0.3s ease, border-color 0.3s ease;
            border: 1px solid #4682B4;
        }
        .stButton>button[kind="primary"] {
            background-color: #4682B4;
            color: white;
        }
        .stButton>button[kind="primary"]:hover {
            background-color: #3a6d96;
            border-color: #3a6d96;
        }
        .stButton>button[kind="primary"]:focus {
             box-shadow: 0 0 0 2px rgba(70, 130, 180, 0.5);
             outline: none;
        }
        .stDataFrame {
            border: 1px solid #e0e0e0;
            border-radius: 5px;
        }
        .stProgress > div > div > div > div {
            background-color: #4682B4;
        }
        .stAlert {
            border-radius: 5px;
            border-left: 5px solid;
            padding: 0.8rem 1rem;
        }
        .stAlert[data-baseweb="notification"][kind="info"] {
            border-left-color: #4682B4;
            background-color: #e7f3fe;
        }
        .stAlert[data-baseweb="notification"][kind="success"] {
            border-left-color: #28a745;
            background-color: #eaf7ec;
        }
        .stAlert[data-baseweb="notification"][kind="warning"] {
            border-left-color: #ffc107;
            background-color: #fff8e1;
        }
         .stAlert[data-baseweb="notification"][kind="error"] {
            border-left-color: #dc3545;
            background-color: #fdecea;
        }
        #MainMenu {visibility: hidden;}
        .stDeployButton {visibility: hidden;}
        footer {visibility: hidden;}
        div[data-testid="stToolbar"] {visibility: hidden;}
        div[data-testid="stDecoration"] {visibility: hidden;}
        div[data-testid="stStatusWidget"] {visibility: hidden;}
    </style>
"""
st.markdown(app_style, unsafe_allow_html=True)

st.title("🏠 ListingLens Property Extractor")
st.markdown("Welcome to ListingLens! Paste property listing web addresses (one per line) below. The tool will visit each page, attempt to reveal hidden details, extract relevant sections, use AI to analyze the content, and present key details in a table. You can download successful results as a CSV file.")

urls_input = st.text_area(
    "Enter Listing URLs (one per line):",
    height=150,
    placeholder=(
        "e.g., https://www.property-website.com/listing123\n"
        "https://www.another-site.com/for-sale/property-abc\n"
        "https://www.iproperty.com.my/property/kuala-lumpur/condo-for-sale-123456/\n"
        "https://www.edgeprop.my/listing/sale/12345/selangor/serviced-residence"
    )
)

if st.button("🔍 Extract Details from URLs", type="primary"):
    batch_start_time = time.perf_counter()

    raw_urls = [url.strip() for url in urls_input.splitlines() if url.strip()]
    valid_urls = []
    invalid_inputs = []
    for url in raw_urls:
        try:
            result = urlparse(url)
            if all([result.scheme in ['http', 'https'], result.netloc]):
                valid_urls.append(url)
            else:
                invalid_inputs.append(f"'{url}' (invalid format)")
        except ValueError:
            invalid_inputs.append(f"'{url}' (could not parse)")

    if invalid_inputs:
        st.warning(f"⚠️ Some inputs were not valid web addresses and will be ignored: {', '.join(invalid_inputs)}")

    if not valid_urls:
        st.warning("⚠️ Please enter at least one valid web address (URL) starting with http:// or https://.")
    else:
        total_urls = len(valid_urls)
        st.info(f"Starting extraction for {total_urls} web address(es)...")
        logger.info(f"User initiated extraction for {total_urls} valid URLs. Max workers: {MAX_CONCURRENT_WORKERS}")

        all_results = []
        progress_bar = st.progress(0.0)
        status_text = st.empty()
        processed_count = 0

        spinner_message = f"⚙️ Processing {total_urls} address(es)... This may take a few minutes."
        with st.spinner(spinner_message):
            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENT_WORKERS) as executor:
                future_to_url = {executor.submit(process_url, url): url for url in valid_urls}
                for future in concurrent.futures.as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        result = future.result()
                        all_results.append(result)
                    except Exception as exc:
                        process_time = time.perf_counter() - batch_start_time
                        logger.error(f"Critical exception processing {url} after ~{process_time:.2f}s: {exc}", exc_info=True)
                        all_results.append({"url": url, "error": f"Critical processing error: {exc}", "processing_time_seconds": round(process_time, 2)})
                    finally:
                        processed_count += 1
                        progress_percentage = min(processed_count / total_urls, 1.0)
                        status_text.text(f"Processed {processed_count} of {total_urls} addresses...")
                        progress_bar.progress(progress_percentage)

        status_text.text(f"Extraction complete! Processed {processed_count} of {total_urls} addresses.")
        time.sleep(2)
        status_text.empty()
        progress_bar.empty()

        successful_extractions = [res for res in all_results if not res.get("error")]
        failed_extractions = [res for res in all_results if res.get("error")]

        st.markdown("---")

        if successful_extractions:
            st.success(f"✅ Successfully extracted details from {len(successful_extractions)} address(es).")
            st.subheader("Extracted Property Details:")
            df_success = pd.DataFrame(successful_extractions)
            current_cols = df_success.columns.tolist()
            ordered_cols = []
            for col in COLUMN_ORDER:
                if col in current_cols and col != 'error':
                    ordered_cols.append(col)
            remaining_cols = [col for col in current_cols if col not in ordered_cols and col != 'error']
            final_cols_success = [col for col in ordered_cols + remaining_cols if col in df_success.columns]
            df_success_display = df_success[final_cols_success].fillna('N/A')
            st.dataframe(df_success_display)
            csv_data = df_success_display.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="⬇️ Download Successful Results as CSV",
                data=csv_data,
                file_name='property_data_successful.csv',
                mime='text/csv',
                key='download-csv'
            )
        else:
            if total_urls > 0:
                st.info("ℹ️ No data was successfully extracted from the provided addresses. Check errors below.")

        if failed_extractions:
            with st.expander(f"⚠️ View Processing Issues & Errors ({len(failed_extractions)} URLs)", expanded=True):
                st.warning(f"Failed to process or extract full details for {len(failed_extractions)} address(es). See details below.")
                df_failed = pd.DataFrame(failed_extractions)
                current_cols_failed = df_failed.columns.tolist()
                fail_order = ['url', 'error', 'processing_time_seconds']
                ordered_cols_failed = [col for col in fail_order if col in current_cols_failed]
                remaining_cols_failed = [col for col in current_cols_failed if col not in ordered_cols_failed]
                final_cols_failed = [col for col in ordered_cols_failed + remaining_cols_failed if col in df_failed.columns]
                df_failed_display = df_failed[final_cols_failed].fillna('N/A')
                st.dataframe(df_failed_display, use_container_width=True)
                logger.warning(f"Failed/Partial URLs ({len(failed_extractions)}): {[res.get('url') for res in failed_extractions]}")

        batch_end_time = time.perf_counter()
        total_duration = batch_end_time - batch_start_time
        st.info(f"⏱️ Total processing time for the batch: {total_duration:.2f} seconds.")
        logger.info(f"Total batch processing finished in {total_duration:.2f} seconds for {total_urls} initial URLs.")

st.markdown("---")
st.caption("ListingLens Extractor")