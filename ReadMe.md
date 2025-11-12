# ListingLens Property Data Extractor

ListingLens is a Streamlit application that automates the collection of property listing details from public real-estate portals. It combines Selenium-driven browser automation with Google's Gemini generative AI to interpret the page contents and deliver clean, structured data that is ready for market research, lead management, or portfolio analysis.

---

## Table of Contents
1. [Key Capabilities](#key-capabilities)
2. [System Architecture](#system-architecture)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
5. [Configuring API Secrets](#configuring-api-secrets)
6. [Running the App](#running-the-app)
7. [Using ListingLens](#using-listinglens)
8. [Output Data Fields](#output-data-fields)
9. [Logs & Troubleshooting](#logs--troubleshooting)
10. [Customization Tips](#customization-tips)
11. [Limitations & Considerations](#limitations--considerations)
12. [Support](#support)

---

## Key Capabilities
- **Automated page interaction:** Selenium opens each listing URL, loads dynamic content, expands “show more” sections, and reveals hidden contact numbers where possible.
- **AI-powered extraction:** Google's `gemini-2.0-flash` model converts the captured HTML snippets into structured property metadata with consistent keys.
- **Batch processing:** A ThreadPoolExecutor (maximum of 5 workers by default) enables concurrent scraping of multiple URLs, providing responsive feedback in the Streamlit UI.
- **Results dashboard:** Successful extractions are displayed in an interactive table and can be downloaded as a CSV; failures are summarized separately with captured error messages.
- **Detailed telemetry:** Rich logging surfaces Selenium actions, AI responses, and runtime durations to simplify debugging and performance analysis.

## System Architecture
| Layer | Responsibility |
| --- | --- |
| **Streamlit UI (`listinglens.py`)** | Captures user input (list of URLs), orchestrates the scrape/analyze workflow, and renders results, progress, and download buttons. |
| **Selenium Automation** | Launches a headless Chromium browser (`/usr/bin/chromium` + `/usr/bin/chromedriver`), applies targeted CSS selectors, and gathers HTML blocks from sections such as contact cards, listing details, descriptions, and property facts. |
| **AI Extraction (`google-generativeai`)** | Sends the combined HTML to Gemini, requesting normalized JSON with fields like price, square footage, bedrooms, etc. |
| **Concurrency Layer** | Uses `concurrent.futures.ThreadPoolExecutor` to process URLs in parallel while updating a Streamlit progress bar. |
| **Logging (`property_scraper.log`)** | Captures informative and error logs from scraping and AI phases to aid monitoring and support. |

## Prerequisites
- **Python:** 3.9 or newer (Streamlit officially supports 3.8+, and Selenium requires 3.8+).
- **Browser runtime:** Chromium and the matching Chromedriver available on the host (the app defaults to `/usr/bin/chromium` and `/usr/bin/chromedriver`).
- **Google Generative AI access:** A valid API key with permission to call Gemini models.
- **Network access:** Outbound HTTPS access to the target listing sites and the Gemini API endpoint.

## Installation
```bash
# Clone the repository
git clone https://github.com/<your-org>/ListingLens.git
cd ListingLens

# (Recommended) create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Install system packages if they are not already present (Linux example)
sudo apt-get update
sudo apt-get install -y chromium-browser chromium-chromedriver
```
If you are deploying on Streamlit Community Cloud, add `chromium` and `chromium-driver` to `packages.txt` so that the build process installs the correct binaries.

## Configuring API Secrets
ListingLens expects the Google API key in Streamlit's secrets management system:
1. Create (or update) `.streamlit/secrets.toml` in the project root.
2. Add your key:
   ```toml
   GOOGLE_API_KEY = "your-gemini-api-key"
   ```
3. When running on Streamlit Cloud, configure the same secret in the project settings.

At runtime the app validates that `GOOGLE_API_KEY` is present; the UI stops with an error if the key cannot be loaded.

## Running the App
```bash
streamlit run listinglens.py
```
The Streamlit server will output a local URL (typically `http://localhost:8501`). Open the link in your browser to access the interface.

## Using ListingLens
1. **Prepare your URLs:** Gather the property listing pages you want to analyze (each must start with `http://` or `https://`).
2. **Paste into the text area:** Enter one URL per line in the “Enter Listing URLs” input.
3. **Start extraction:** Click **“🔍 Extract Details from URLs”**. The app validates each address and launches concurrent scraping jobs.
4. **Monitor progress:** A progress bar, status text, and spinner indicate how many URLs have completed.
5. **Review results:**
   - Successful rows appear in a data table. You can download the structured dataset via the “⬇️ Download Successful Results as CSV” button.
   - Failures (timeouts, missing data, AI parsing issues, etc.) are listed in an expandable section together with diagnostic messages.
6. **Check total runtime:** Once finished, the interface reports the total processing time for the batch.

## Output Data Fields
Gemini is prompted to produce the following keys for every processed listing:
- `url`
- `listing_title`
- `project_name`
- `area`
- `state`
- `price` (integer, currency symbols removed)
- `sq_ft` (integer square footage)
- `bedrooms`
- `bathrooms`
- `property_type`
- `carpark`
- `floor_range`
- `phone_number`
- `description`
- `processing_time_seconds`
- `error` (populated when scraping or AI analysis fails)

The Streamlit table automatically prioritizes these fields but still surfaces any additional keys returned by the AI for transparency.

## Logs & Troubleshooting
- **Console & Streamlit logs:** Selenium actions, button clicks, waits, and timing statements stream to the terminal where Streamlit is running.
- **`property_scraper.log`:** Aggregates INFO/WARNING/ERROR messages, including raw stack traces for unexpected failures. Share this file when requesting support.
- **Common issues:**
  - *Missing Chromium binaries:* Ensure `chromium` and `chromium-driver` are installed and that `chrome_options.binary_location` points to the correct path.
  - *Blocked pop-ups or dynamic content:* Some listings may require authentication or heavy JavaScript. Adjust the target selectors or wait times as described below.
  - *Gemini quota errors:* Verify your API key limits and billing status if AI extraction fails frequently.

## Customization Tips
- **Adjust concurrency:** Modify `MAX_CONCURRENT_WORKERS` in `listinglens.py` to tune throughput versus resource usage.
- **Update selectors:** `target_css_selectors` controls which page sections are scraped. Add or refine CSS selectors to capture new data blocks for different real-estate portals.
- **Extend data fields:** Update the Gemini prompt inside `extract_property_details` if you need additional attributes. Ensure you update downstream display logic to include new columns.
- **Modify browser options:** Tweak `chrome_options` (e.g., user-agent, window size, timeouts) if a target site behaves differently in headless mode.

## Limitations & Considerations
- **Respect site policies:** Always review and comply with the terms of service of the websites you target.
- **Dynamic or protected content:** Listings behind logins, CAPTCHAs, or bot protections may not be accessible without additional integration work.
- **AI fallbacks:** When Gemini cannot parse the HTML into valid JSON, the app records the raw error message; manual review may be required.
- **Performance envelopes:** High concurrency or very large batches can be CPU- and memory-intensive, especially on resource-constrained hosting environments.

## Support
For assistance or feature requests, contact **Weldon Tan** at [weldontan.pro@gmail.com](mailto:weldontan.pro@gmail.com).
