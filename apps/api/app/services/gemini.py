import google.generativeai as genai
import json
import structlog
import time
from app.core.config import settings

logger = structlog.get_logger()

genai.configure(api_key=settings.GOOGLE_API_KEY)

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

HTML Content:
```html
{html_content}
```
"""

async def extract_property_details(html_content: str, listing_url: str):
    if not html_content or html_content.isspace():
        logger.warning("gemini.empty_html", url=listing_url)
        return {"url": listing_url, "error": "No HTML content extracted from page to analyze."}
    
    logger.info("gemini.start", url=listing_url)
    start_time = time.perf_counter()
    
    max_retries = 3
    retry_delay = 2

    safety_settings = {
        genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
        genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: genai.types.HarmBlockThreshold.BLOCK_NONE,
        genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: genai.types.HarmBlockThreshold.BLOCK_NONE,
        genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
    }

    for attempt in range(max_retries):
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            prompt = PROPERTY_EXTRACTION_PROMPT.format(html_content=html_content)
            
            # Gemini python client is synchronous for now in most examples, 
            # but we can run it in a thread if needed. For Celery worker it's fine.
            response = model.generate_content(prompt, safety_settings=safety_settings)
            
            try:
                json_string = response.text.strip().strip('```json').strip('```').strip()
            except ValueError:
                finish_reason = "Unknown"
                if response.candidates:
                    finish_reason = response.candidates[0].finish_reason
                
                logger.warning("gemini.blocked", url=listing_url, attempt=attempt+1, reason=finish_reason)
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    return {"url": listing_url, "error": f"AI generation failed after {max_retries} attempts. Finish Reason: {finish_reason}"}
            
            try:
                data = json.loads(json_string)
                if isinstance(data, dict):
                     data['url'] = listing_url
                     duration = time.perf_counter() - start_time
                     logger.info("gemini.success", url=listing_url, duration=duration)
                     return data
                else:
                     logger.warning("gemini.invalid_json_type", url=listing_url, json=json_string[:100])
                     if attempt < max_retries - 1:
                         time.sleep(retry_delay)
                         continue
                     return {"url": listing_url, "error": "AI output was not a valid JSON object."}
            except json.JSONDecodeError as json_err:
                 logger.error("gemini.json_parse_error", url=listing_url, error=str(json_err))
                 if attempt < max_retries - 1:
                     time.sleep(retry_delay)
                     continue
                 return {"url": listing_url, "error": f"Failed to parse AI response: {json_err}"}
                 
        except Exception as e:
            logger.error("gemini.exception", url=listing_url, attempt=attempt+1, error=str(e))
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                return {"url": listing_url, "error": f"Gemini API call failed: {str(e)}"}
