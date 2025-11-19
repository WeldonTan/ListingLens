import time
import structlog
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, StaleElementReferenceException, WebDriverException
)
from app.core.config import settings

logger = structlog.get_logger()

# --- Constants ---
PAGE_LOAD_TIMEOUT = 30.0  # Increased for slower sites like Mudah
BUTTON_WAIT_TIMEOUT = 5.0
POST_CLICK_DELAY = 0.1    # Reduced for optimization
POST_EXPANSION_CLICK_DELAY = 0.1 # Reduced for optimization
DELAY_BEFORE_POST_EXPANSION_SEARCH = 0.1 # Reduced for optimization
SECOND_EXPANSION_CLICK_DELAY = 0.1 # Reduced for optimization
POST_SECOND_EXPANSION_CLICK_DELAY = 0.1 # Reduced for optimization
EXTRACTION_WAIT_TIMEOUT = 0.1 # Reduced for optimization
INITIAL_SETTLE_DELAY = 0.1 # Reduced for optimization

TARGET_CSS_SELECTORS = [
    "script[id='__NEXT_DATA__']",
    "script[type='application/ld+json']",
    "body"
]

INITIAL_BUTTON_XPATHS = [
    "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'view number')]",
    "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show more')]",
    "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'reveal phone')]",
    "//button[contains(text(),'01')]",
    "//button[@aria-label='Show phone number']",
    "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show more')]",
    "//span[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'view number')]",
    "//div[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'view number')]",
    "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'click to show')]",
]

EXPANSION_BUTTON_TEXTS = ["show more", "read more", "view more"]

POST_EXPANSION_CONTACT_XPATHS = [
    "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show contact number')]",
    "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show contact number')]",
    "//div[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show contact number')]",
]

def click_button(driver, button_element, xpath_description, wait_timeout, post_click_delay):
    try:
        if button_element and button_element.is_displayed() and button_element.is_enabled():
            try: # First, wait for the element to be clickable
                WebDriverWait(driver, wait_timeout).until(
                    EC.element_to_be_clickable((By.XPATH, xpath_description))
                )
            except TimeoutException: # If not clickable after timeout, proceed to click anyway
                pass

            try:
                # Scroll to element and click using JavaScript for robustness
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button_element)
                driver.execute_script("arguments[0].click();", button_element)
                time.sleep(post_click_delay) # Short delay for DOM to settle
                return True
            except StaleElementReferenceException:
                 try: # If StaleElementReferenceException, re-find the element and try again
                     button_fresh = WebDriverWait(driver, wait_timeout).until(
                        EC.presence_of_element_located((By.XPATH, xpath_description))
                     )
                     driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button_fresh)
                     driver.execute_script("arguments[0].click();", button_fresh)
                     time.sleep(post_click_delay)
                     return True
                 except Exception:
                     pass
            except Exception:
                pass
    except Exception:
        pass
    return False

def scrape_url(url: str):
    logger.info("scraper.start", url=url)
    
    chrome_options = Options()
    chrome_options.page_load_strategy = 'eager'
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    driver = None
    extracted_html_list = []
    error = None

    try:
        driver = webdriver.Remote(
            command_executor=settings.SELENIUM_GRID_URL,
            options=chrome_options
        )
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)

        driver.get(url)
        WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        )
        
        time.sleep(INITIAL_SETTLE_DELAY)

        # Interaction Logic (Simplified for brevity but keeping core logic)
        expansion_buttons_clicked = []
        for xpath in INITIAL_BUTTON_XPATHS:
            is_expansion = any(txt in xpath.lower() for txt in EXPANSION_BUTTON_TEXTS)
            try:
                buttons = driver.find_elements(By.XPATH, xpath)
                for i, btn in enumerate(buttons):
                    specific_xpath = f"({xpath})[{i+1}]"
                    if click_button(driver, btn, specific_xpath, BUTTON_WAIT_TIMEOUT, POST_CLICK_DELAY):
                        if is_expansion:
                            expansion_buttons_clicked.append(specific_xpath)
            except Exception:
                pass

        if expansion_buttons_clicked:
             time.sleep(SECOND_EXPANSION_CLICK_DELAY)
             for specific_xpath in expansion_buttons_clicked:
                 try:
                     btn = driver.find_element(By.XPATH, specific_xpath)
                     click_button(driver, btn, specific_xpath, BUTTON_WAIT_TIMEOUT, POST_SECOND_EXPANSION_CLICK_DELAY)
                 except Exception:
                     pass
        
        time.sleep(DELAY_BEFORE_POST_EXPANSION_SEARCH)
        
        for xpath in POST_EXPANSION_CONTACT_XPATHS:
             try:
                buttons = driver.find_elements(By.XPATH, xpath)
                for i, btn in enumerate(buttons):
                    specific_xpath = f"({xpath})[{i+1}]"
                    click_button(driver, btn, specific_xpath, BUTTON_WAIT_TIMEOUT, POST_EXPANSION_CLICK_DELAY)
             except Exception:
                 pass

        # Extraction
        for selector in TARGET_CSS_SELECTORS:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed() or selector == "script[type='application/ld+json']" or selector == "script[id='__NEXT_DATA__']":
                        html = element.get_attribute('outerHTML')
                        if html:
                            extracted_html_list.append(html.strip())
            except Exception:
                pass

    except Exception as e:
        error = str(e)
        logger.error("scraper.error", url=url, error=error)
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    combined_html = "\n\n".join(extracted_html_list) if extracted_html_list else None
    return {"url": url, "html": combined_html, "error": error}
