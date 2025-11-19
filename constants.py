# --- Configuration Constants ---
MAX_CONCURRENT_WORKERS = 3  # Reduced for stability

# --- Timing Constants (Seconds) ---
PAGE_LOAD_TIMEOUT = 10.0  # Increased for reliability
BUTTON_WAIT_TIMEOUT = 3.0
POST_CLICK_DELAY = 0.5
POST_EXPANSION_CLICK_DELAY = 0.5
DELAY_BEFORE_POST_EXPANSION_SEARCH = 0.5
SECOND_EXPANSION_CLICK_DELAY = 0.5
POST_SECOND_EXPANSION_CLICK_DELAY = 0.5
EXTRACTION_WAIT_TIMEOUT = 0.5
INITIAL_SETTLE_DELAY = 0.5

# --- Data Structure Constants ---
COLUMN_ORDER = [
    'url', 'listing_title', 'project_name', 'price', 'area', 'state',
    'sq_ft', 'bedrooms', 'bathrooms',
    'property_type', 'carpark', 'floor_range',
    'phone_number', 'description',
    'processing_time_seconds', 'error'
]

# --- CSS Selectors ---
TARGET_CSS_SELECTORS = [
    "script[id='__NEXT_DATA__']",  # Next.js Data - Priority for raw data
    "script[type='application/ld+json']",  # JSON-LD Data
    "body"  # Fallback: Analyze the entire page content. Robust but token-heavy.
]

# --- XPath Selectors ---
INITIAL_BUTTON_XPATHS = [
    "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'view number')]",
    "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show more')]",
    "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'reveal phone')]",
    "//button[contains(text(),'01')]",  # Specific for Mudah.my style buttons
    "//button[@aria-label='Show phone number']",  # Metadata based selector
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

# --- Gemini Prompts ---
PROPERTY_EXTRACTION_PROMPT = """
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
