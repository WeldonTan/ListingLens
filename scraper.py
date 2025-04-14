import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException, StaleElementReferenceException
import traceback # Keep for detailed error logging
from bs4 import BeautifulSoup # For parsing HTML text

# --- Configuration ---
CHROME_DRIVER_PATH = r'C:\Users\estan\Documents\GitHub\Playground\chromedriver-win64\chromedriver.exe' # <--- UPDATE THIS PATH (Keep your original path)

# Timeouts (in seconds)
PAGE_LOAD_TIMEOUT = 4 # Increased timeout slightly, pages can be slow
BUTTON_WAIT_TIMEOUT = 2 # Longer wait specifically for buttons to become clickable
POST_CLICK_DELAY = 1.5    # Wait longer after clicking, for content reveal/state changes
POST_EXPANSION_CLICK_DELAY = 1.5 # Shorter delay after clicking a secondary button like 'show contact number'
DELAY_BEFORE_POST_EXPANSION_SEARCH = 1.5 # Seconds to wait after initial clicks finish
SECOND_EXPANSION_CLICK_DELAY = 1.0 # Delay between first and second click on 'show more'
POST_SECOND_EXPANSION_CLICK_DELAY = 1.5 # Delay after the *second* click on 'show more'

# --- Selenium Options ---
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--enable-unsafe-swiftshader")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36") # Updated User Agent
chrome_options.add_argument("--log-level=3") # Suppress excessive Selenium logging
chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

# --- Helper Function for Elapsed Time ---
def format_elapsed_time(start_time: float) -> str:
    """Formats the elapsed time since start_time as a string."""
    elapsed = time.time() - start_time
    return f"[+{elapsed:.2f}s]"

# --- Helper Function for Clicking Buttons ---
def click_button(driver, button_element, xpath_description, wait_timeout, post_click_delay, start_time_for_logging, click_attempt_description=""):
    """Attempts to click a button element with robust handling."""
    clicked = False
    btn_text = "(unknown)" # Default text
    try:
        # Check if the specific button instance is visible and enabled before waiting/clicking
        if button_element and button_element.is_displayed() and button_element.is_enabled():
            # Wait specifically for this button to be clickable using its specific XPath
            button_to_click = WebDriverWait(driver, wait_timeout).until(
                EC.element_to_be_clickable((By.XPATH, xpath_description)) # Re-find using XPath for clickability check
            )

            # Get button text for logging before click (handle potential staleness)
            try:
                # Re-fetch the element just before interacting
                button_to_click = driver.find_element(By.XPATH, xpath_description)
                btn_text = button_to_click.text.strip().replace('\n', ' ')[:50] # Get first 50 chars
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

            # Try clicking with JavaScript
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button_to_click)
                time.sleep(0.5) # Short pause after scroll, before click
                driver.execute_script("arguments[0].click();", button_to_click)
                clicked = True
                print(f"{format_elapsed_time(start_time_for_logging)}     {click_attempt_description}Clicked button: '{btn_text}' using XPath: {xpath_description}")
                time.sleep(post_click_delay) # Wait for action to complete
                print(f"{format_elapsed_time(start_time_for_logging)}     Post-click delay ({post_click_delay}s) finished for '{btn_text}'.")
            except StaleElementReferenceException:
                 print(f"{format_elapsed_time(start_time_for_logging)}     StaleElementReferenceException during JS click for XPath: {xpath_description}. Re-finding...")
                 try:
                     time.sleep(0.5)
                     button_fresh = driver.find_element(By.XPATH, xpath_description)
                     driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button_fresh)
                     time.sleep(0.5)
                     driver.execute_script("arguments[0].click();", button_fresh)
                     clicked = True
                     print(f"{format_elapsed_time(start_time_for_logging)}     {click_attempt_description}Clicked button (after re-find): '{btn_text}' using XPath: {xpath_description}")
                     time.sleep(post_click_delay)
                     print(f"{format_elapsed_time(start_time_for_logging)}     Post-click delay ({post_click_delay}s) finished for '{btn_text}'.")
                 except Exception as e_retry_click:
                     print(f"{format_elapsed_time(start_time_for_logging)}     Error clicking button after re-find for XPath '{xpath_description}': {type(e_retry_click).__name__}")
            except Exception as e_js_click:
                 print(f"{format_elapsed_time(start_time_for_logging)}     Error during JS click for XPath '{xpath_description}': {type(e_js_click).__name__}")

        # else: # Debugging: Log if button found but not interactable
        #     is_disp = button_element.is_displayed() if button_element else 'N/A'
        #     is_ena = button_element.is_enabled() if button_element else 'N/A'
        #     print(f"{format_elapsed_time(start_time_for_logging)}     Button found but not displayed({is_disp})/enabled({is_ena}) for XPath: {xpath_description}")

    except TimeoutException:
        # print(f"{format_elapsed_time(start_time_for_logging)}     Button found but timed out waiting to be clickable for XPath: {xpath_description}")
        pass # Button found but wasn't clickable in time
    except StaleElementReferenceException:
        print(f"{format_elapsed_time(start_time_for_logging)}     StaleElementReferenceException checking/waiting for button with XPath: {xpath_description}. Page might have updated.")
        pass # Element reference is no longer valid
    except NoSuchElementException:
        print(f"{format_elapsed_time(start_time_for_logging)}     NoSuchElementException when trying to re-find button for clickability check/JS click: {xpath_description}.")
        pass # Element disappeared
    except ElementClickInterceptedException:
        print(f"{format_elapsed_time(start_time_for_logging)}     ElementClickInterceptedException for button with XPath: {xpath_description}. Another element may be blocking.")
        pass # Click was blocked
    except Exception as e_click:
        print(f"{format_elapsed_time(start_time_for_logging)}     Error clicking button instance with XPath '{xpath_description}': {type(e_click).__name__} - {e_click}")
        pass
    return clicked, btn_text # Return text for logging summary

# --- Function to Scrape Targeted Sections ---

def scrape_targeted_sections(url: str, target_selectors: list[str]):
    """
    Loads a URL, clicks potential reveal buttons (including multi-step reveals like double-clicking 'show more'),
    and extracts HTML only from elements matching the provided CSS selectors.
    Includes elapsed time logging.

    Args:
        url (str): The web address of the property listing.
        target_selectors (list[str]): A list of CSS selectors identifying the
                                      HTML sections/elements to extract.

    Returns:
        dict: A dictionary containing:
              - 'url': The original URL processed.
              - 'extracted_data' (dict): A dictionary where keys are the target_selectors
                                         and values are lists of outer HTML strings found
                                         for each selector.
              - 'error' (str): An error message if scraping failed, otherwise None.
    """
    print(f"Processing URL: {url}")
    driver = None
    start_time = time.time() # Start timing for this specific URL
    # Initialize result with extracted_data as a dictionary
    result = {"url": url, "extracted_data": {selector: [] for selector in target_selectors}, "error": None}

    # --- Define Button XPaths ---
    initial_button_xpaths = [
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'view number')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show phone')]",
        "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show phone')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show more')]", # Expansion button
        "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'read more')]",      # Expansion button
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'lihat nombor')]",
        "//span[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'view number')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'tunjuk nombor telefon')]"
    ]
    expansion_button_texts = ["show more", "read more"] # Keywords to identify expansion buttons for potential double click

    post_expansion_contact_xpaths = [
         "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show contact number')]",
         "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show contact number')]",
         "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show contact')]",
         "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show contact')]",
    ]

    try:
        # --- Setup WebDriver ---
        if not os.path.exists(CHROME_DRIVER_PATH):
            raise FileNotFoundError(f"ChromeDriver not found at: {CHROME_DRIVER_PATH}")
        service = ChromeService(executable_path=CHROME_DRIVER_PATH)
        print(f"{format_elapsed_time(start_time)} Initializing WebDriver...")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        print(f"{format_elapsed_time(start_time)} WebDriver initialized.")

        # --- Load Page ---
        print(f"{format_elapsed_time(start_time)} Loading page...")
        driver.get(url)
        WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body')) # Wait for body tag
        )
        print(f"{format_elapsed_time(start_time)} Page loaded.")
        initial_settle_delay = 3.0
        print(f"{format_elapsed_time(start_time)} Allowing {initial_settle_delay}s for initial elements to settle...")
        time.sleep(initial_settle_delay)
        print(f"{format_elapsed_time(start_time)} Post-load delay finished.")

        # --- Click Initial Reveal/Expansion Buttons ---
        print(f"{format_elapsed_time(start_time)} Attempting to click initial reveal/expansion buttons...")
        initial_click_attempts = 0
        clicked_initial_button_texts = []
        expansion_buttons_clicked = [] # Keep track of specific expansion buttons clicked once

        for xpath in initial_button_xpaths:
            is_expansion_xpath = any(txt in xpath for txt in expansion_button_texts)
            try:
                potential_buttons = driver.find_elements(By.XPATH, xpath)
                if not potential_buttons:
                    continue

                for i, button in enumerate(potential_buttons):
                    specific_xpath = f"({xpath})[{i+1}]" # XPath indexes are 1-based
                    try:
                        # Pass the button element found initially for the is_displayed/is_enabled check
                        clicked, btn_text = click_button(driver, button, specific_xpath, BUTTON_WAIT_TIMEOUT, POST_CLICK_DELAY, start_time, click_attempt_description="(Attempt 1) ")
                        if clicked:
                            initial_click_attempts += 1
                            clicked_initial_button_texts.append(f"'{btn_text}...'")
                            if is_expansion_xpath:
                                # Store the specific xpath of the expansion button clicked
                                expansion_buttons_clicked.append(specific_xpath)
                            # Optional: Break if only one click of this type is needed (e.g., only one 'show more')
                            # if is_expansion_xpath:
                            #    break # Uncomment if you only ever want to click the *first* 'show more' found
                    except Exception as e_inner_click:
                         # Log error during the click attempt for a specific button instance
                         print(f"{format_elapsed_time(start_time)}     Error processing button {i+1} for XPath '{xpath}': {type(e_inner_click).__name__}")


            except StaleElementReferenceException:
                 print(f"{format_elapsed_time(start_time)}   StaleElementReferenceException while finding initial buttons for XPath '{xpath}'. Skipping rest for this XPath.")
            except Exception as e_find:
                 print(f"{format_elapsed_time(start_time)}   Error finding/processing elements with initial XPath '{xpath}': {type(e_find).__name__} - {e_find}")

        # --- Attempt Second Click on Expansion Buttons if Necessary ---
        if expansion_buttons_clicked:
            print(f"{format_elapsed_time(start_time)} Pausing {SECOND_EXPANSION_CLICK_DELAY}s before attempting second click on expansion buttons...")
            time.sleep(SECOND_EXPANSION_CLICK_DELAY)
            print(f"{format_elapsed_time(start_time)} Attempting second click on {len(expansion_buttons_clicked)} expansion button(s)...")
            second_click_success_count = 0
            for specific_xpath in expansion_buttons_clicked:
                try:
                    # Re-find the button element just before the second click attempt
                    button_element_for_second_click = driver.find_element(By.XPATH, specific_xpath)
                    # Use a potentially different post-click delay for the second click
                    clicked, btn_text = click_button(driver, button_element_for_second_click, specific_xpath, BUTTON_WAIT_TIMEOUT, POST_SECOND_EXPANSION_CLICK_DELAY, start_time, click_attempt_description="(Attempt 2) ")
                    if clicked:
                        second_click_success_count += 1
                        # Optionally update the clicked texts list or just log here
                        print(f"{format_elapsed_time(start_time)}     Successfully performed second click on: '{btn_text}'")
                except NoSuchElementException:
                    print(f"{format_elapsed_time(start_time)}     Could not re-find expansion button for second click: {specific_xpath}")
                except Exception as e_second_click:
                    print(f"{format_elapsed_time(start_time)}     Error during second click attempt for XPath '{specific_xpath}': {type(e_second_click).__name__}")
            if second_click_success_count > 0:
                 print(f"{format_elapsed_time(start_time)} Second click attempted successfully on {second_click_success_count} expansion button(s).")


        if initial_click_attempts > 0:
            # Log summary of first clicks
            print(f"{format_elapsed_time(start_time)} Initial click phase completed. Attempted clicks on: {', '.join(clicked_initial_button_texts)}")
        else:
            print(f"{format_elapsed_time(start_time)} No initial reveal/expansion buttons found or clicked.")


        # --- Delay Before Searching for Post-Expansion Buttons ---
        print(f"{format_elapsed_time(start_time)} Pausing {DELAY_BEFORE_POST_EXPANSION_SEARCH}s after initial/second clicks before searching for post-expansion buttons...")
        time.sleep(DELAY_BEFORE_POST_EXPANSION_SEARCH)
        print(f"{format_elapsed_time(start_time)} Pause finished. Proceeding with post-expansion search.")


        # --- Click Post-Expansion Contact Buttons ---
        print(f"{format_elapsed_time(start_time)} Attempting to click post-expansion contact buttons...")
        post_expansion_clicks = 0
        clicked_post_expansion_texts = []

        for xpath in post_expansion_contact_xpaths:
             try:
                potential_buttons = driver.find_elements(By.XPATH, xpath)
                if not potential_buttons:
                    continue

                for i, button in enumerate(potential_buttons):
                    specific_xpath = f"({xpath})[{i+1}]"
                    try:
                        clicked, btn_text = click_button(driver, button, specific_xpath, BUTTON_WAIT_TIMEOUT, POST_EXPANSION_CLICK_DELAY, start_time)
                        if clicked:
                             post_expansion_clicks += 1
                             clicked_post_expansion_texts.append(f"'{btn_text}...'")
                             # Optional: Break if only one click of this type is needed
                             # break
                    except Exception as e_inner_click:
                         print(f"{format_elapsed_time(start_time)}     Error processing post-expansion button {i+1} for XPath '{xpath}': {type(e_inner_click).__name__}")


             except StaleElementReferenceException:
                 print(f"{format_elapsed_time(start_time)}   StaleElementReferenceException while finding post-expansion buttons for XPath '{xpath}'. Skipping rest for this XPath.")
             except Exception as e_find:
                 print(f"{format_elapsed_time(start_time)}   Error finding/processing elements with post-expansion XPath '{xpath}': {type(e_find).__name__} - {e_find}")

        if post_expansion_clicks > 0:
            print(f"{format_elapsed_time(start_time)} Clicked {post_expansion_clicks} post-expansion contact button(s): {', '.join(clicked_post_expansion_texts)}")
        else:
            print(f"{format_elapsed_time(start_time)} No post-expansion contact buttons found or clicked.")


        # --- Extract Targeted HTML ---
        print(f"{format_elapsed_time(start_time)} Extracting content from target selectors...")
        if not target_selectors:
             print(f"{format_elapsed_time(start_time)} Warning: No target selectors provided.")

        extraction_start_time = time.time()
        # Use the dictionary initialized in 'result'
        extracted_html_dict = result["extracted_data"]

        for i, selector in enumerate(target_selectors):
            selector_start_time = time.time()
            try:
                # Wait briefly for elements matching the selector to be present
                WebDriverWait(driver, 5).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                )
                elements = driver.find_elements(By.CSS_SELECTOR, selector) # Find again after wait
                if elements:
                    print(f"{format_elapsed_time(start_time)}   Found {len(elements)} element(s) for selector: '{selector}' (took {time.time() - selector_start_time:.2f}s)")
                    for element_index, element in enumerate(elements):
                        try:
                            # Check if element is still attached and interactable
                            if element.is_displayed(): # Use is_displayed as a better check for staleness here
                                outer_html = element.get_attribute('outerHTML')
                                if outer_html:
                                    # Append HTML to the list for this specific selector
                                    extracted_html_dict[selector].append(outer_html.strip())
                            else:
                                print(f"{format_elapsed_time(start_time)}     Skipping element {element_index+1} for selector '{selector}' as it seems stale (not displayed).")

                        except StaleElementReferenceException:
                             print(f"{format_elapsed_time(start_time)}     Stale element {element_index+1} encountered getting HTML for selector '{selector}'. Skipping.")
                        except Exception as e_html:
                             print(f"{format_elapsed_time(start_time)}     Error getting HTML for element {element_index+1} selector '{selector}': {type(e_html).__name__}")
                else:
                     print(f"{format_elapsed_time(start_time)}   No elements found for selector: '{selector}' (after waiting {time.time() - selector_start_time:.2f}s)")
            except TimeoutException:
                 print(f"{format_elapsed_time(start_time)}   Timeout waiting for presence of elements for selector: '{selector}' (after {time.time() - selector_start_time:.2f}s)")
            except Exception as e:
                print(f"{format_elapsed_time(start_time)}   Error finding elements for selector '{selector}': {type(e).__name__} - {e} (after {time.time() - selector_start_time:.2f}s)")

        print(f"{format_elapsed_time(start_time)} Finished extraction phase (took {time.time() - extraction_start_time:.2f}s)")

        # Check if any HTML was extracted at all
        if not any(extracted_html_dict.values()):
            print(f"{format_elapsed_time(start_time)} Warning: No HTML content was extracted from any target selectors.")
            # result["error"] = "No content found for target selectors." # Optional: make this an error

    except FileNotFoundError as e:
        print(f"{format_elapsed_time(start_time)} ERROR: {e}")
        result["error"] = str(e)
    except TimeoutException as e:
        err_msg = f"Timeout occurred (Check PAGE_LOAD_TIMEOUT: {PAGE_LOAD_TIMEOUT}s or other waits). Details: {e}"
        print(f"{format_elapsed_time(start_time)} ERROR: {err_msg}")
        result["error"] = err_msg
    except Exception as e:
        err_msg = f"An unexpected error occurred: {type(e).__name__} - {e}\n{traceback.format_exc()}"
        print(f"{format_elapsed_time(start_time)} ERROR: {err_msg}")
        result["error"] = err_msg
    finally:
        if driver:
            print(f"{format_elapsed_time(start_time)} Closing WebDriver...")
            driver.quit()
            print(f"{format_elapsed_time(start_time)} WebDriver closed.")

    total_time = time.time() - start_time
    print(f"Finished processing {url} in {total_time:.2f} seconds.")
    return result

# --- Main Execution ---
if __name__ == "__main__":
    # === List of URLs to Scrape ===
    urls_to_scrape = [
        "https://www.mudah.my/platinum-arena-3r2b-old-klang-road-110695434.htm"
        # Add more URLs here if needed
    ]

    # === List of CSS Selectors for Target Sections ===
    target_css_selectors = [
        "div.Wrapper-ucve63-0.eKOxHS", # Contact Owner block
        "div.style__ParentWrapper-iwjn3z-0.QvHGM", # Listing Details block
        "div.Wrapper-ucve63-0.fKaMDx" # Description block
    ]

    # --- Process URLs ---
    script_start_time = time.time()
    all_results = []
    print("=== Starting Scraping Process ===")
    print(f"Target CSS Selectors: {target_css_selectors}")
    for i, url in enumerate(urls_to_scrape):
        print(f"\n--- Processing URL {i+1}/{len(urls_to_scrape)} ---")
        if not url.startswith("http://") and not url.startswith("https://"):
            print(f"Skipping invalid URL format: {url}")
            all_results.append({"url": url, "extracted_data": {}, "error": "Invalid URL format"})
            continue

        scrape_result = scrape_targeted_sections(url, target_css_selectors)
        all_results.append(scrape_result)
        print("-" * 30)

    script_total_time = time.time() - script_start_time
    print(f"\n=== Finished Processing All URLs in {script_total_time:.2f} seconds ===")

    # --- Print Summary ---
    print("\n=== Scraping Summary ===")
    for result in all_results:
        print(f"\nURL: {result['url']}")
        if result['error']:
            print(f"  Status: Failed")
            print(f"  Error: {result['error']}")
        # Check if the extracted_data dictionary has any content
        elif not result.get('extracted_data') or not any(result['extracted_data'].values()):
            print(f"  Status: Success (but no content extracted for the specified selectors)")
            print(f"  Extracted Content: [None]")
            print(f"  -> Check if the CSS selectors in 'target_css_selectors' are still correct on the live page.")
            print(f"  -> Ensure the target sections actually exist on the page: {url}")
        else:
            print(f"  Status: Success")
            # --- MODIFIED SECTION: Extract and Print Text Previews per Selector ---
            print("  Extracted Text Previews:")
            all_text_for_file = [] # List to hold text from all sections for saving
            try:
                extracted_data = result['extracted_data']
                for selector in target_css_selectors: # Iterate in the order selectors were provided
                    html_parts = extracted_data.get(selector, []) # Get list of HTML for this selector
                    if html_parts:
                        # Join HTML parts found by *this* selector
                        combined_html_for_selector = "\n".join(html_parts)
                        soup = BeautifulSoup(combined_html_for_selector, 'html.parser')
                        # Get text, join lines with spaces, strip extra whitespace
                        text_content = soup.get_text(separator=' ', strip=True)
                        all_text_for_file.append(f"--- Section: {selector} ---\n{text_content}") # Add header for file
                        # Create a preview
                        text_preview = text_content[:250] + ('...' if len(text_content) > 250 else '')
                        print(f"    - Selector '{selector}': {text_preview}")
                    else:
                        print(f"    - Selector '{selector}': [No elements found/extracted]")

            except Exception as e_parse:
                print(f"  Error parsing extracted HTML for text preview: {e_parse}")
                # Fallback: maybe print raw html preview if needed
                # raw_html_preview = str(result['extracted_data'])[:500]
                # print(f"  Raw Extracted Data (Preview): {raw_html_preview}...")

            # --- MODIFIED SECTION: Save Extracted Text to File ---
            if all_text_for_file:
                try:
                    # Create filename, use .txt extension
                    filename_base = url.split('/')[-1].replace('.htm', '').replace('.', '_')
                    filename = f"scraped_text_{filename_base}.txt" # Changed extension to .txt
                    # Join text from all sections with a separator
                    full_text_content = f"Scraped Text from: {result['url']}\n\n" + \
                                        "\n\n==============================\n\n".join(all_text_for_file)

                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(full_text_content)
                    print(f"  Saved extracted TEXT to: {filename}")
                except Exception as e:
                    print(f"  Error saving extracted text to file: {e}")
            else:
                 print("  No text content extracted to save.")
            # --- END OF MODIFIED SECTION ---

    print("\n=== End of Script ===")