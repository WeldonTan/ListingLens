# ListingLens - Property Data Extractor

ListingLens is a Streamlit-powered assistant that automates the tedious work of visiting property listing pages, revealing hidden contact details, collecting the relevant HTML, and using Google's Gemini models to summarise the content into structured data that you can analyse or download. The app orchestrates Selenium-driven browsing, AI post-processing, and convenient CSV exports so that investors, agents, and analysts can focus on decision making instead of manual data entry.

---

## Table of Contents
1. [Key Capabilities](#key-capabilities)
2. [System Architecture](#system-architecture)
3. [Requirements](#requirements)
4. [Initial Setup](#initial-setup)
5. [Configuring the Google Gemini API Key](#configuring-the-google-gemini-api-key)
6. [Running the Streamlit App](#running-the-streamlit-app)
7. [Using the App](#using-the-app)
8. [Output & Downloads](#output--downloads)
9. [Error Handling & Logs](#error-handling--logs)
10. [Customisation Tips](#customisation-tips)
11. [Troubleshooting](#troubleshooting)
12. [Support](#support)

---

## Key Capabilities
- **Automated page interaction:** Launches Chromium via Selenium, waits for the DOM to settle, clicks on buttons such as “show more” or “view number”, and retries with robust error handling so that hidden details are surfaced before extraction.
- **Targeted HTML scraping:** Collects only the sections that matter (contact details, property specs, description blocks) by querying a curated set of CSS selectors, minimising noise in the AI prompt.
- **AI-powered parsing:** Sends the aggregated HTML to the `gemini-2.0-flash` model through the `google-generativeai` SDK to extract a consistent JSON payload containing title, project name, price, location, property details, phone number, and description.
- **Batch processing:** Accepts multiple URLs (one per line) and processes them concurrently (up to five at a time) with progress bars and status updates so you can monitor large workloads.
- **Result dashboards:** Presents successful extractions in a sortable table and exposes a CSV download button while grouping failures with diagnostic messages for quick follow-up.

---

## System Architecture
| Component | File | Responsibility |
|-----------|------|----------------|
| Streamlit UI & Orchestration | `listinglens.py` | Collects URLs, coordinates multi-threaded processing, renders progress indicators, tables, download buttons, and error panels. |
| Selenium Scraper | `listinglens.py` (`scrape_targeted_sections`) & `scraper.py` (reference implementation) | Configures headless Chromium/ChromeDriver, navigates to listings, performs scripted interactions, and extracts HTML by selector. |
| AI Extraction | `listinglens.py` (`extract_property_details`) | Formats prompts for Gemini, validates JSON responses, enriches results with URL metadata, and captures AI parsing errors. |
| Logging | Console + optional `property_scraper.log` | Emits timestamped diagnostics that mirror the terminal output to aid debugging. |

> **Note:** `scraper.py` mirrors the scraping logic for local experimentation (especially on Windows) and highlights where to supply a platform-specific ChromeDriver path.

---

## Requirements
- Python 3.10 or higher.
- Google Gemini API access with a valid API key.
- Google Chrome/Chromium and a matching ChromeDriver binary available on the system PATH (Streamlit Cloud build expects `/usr/bin/chromium` and `/usr/bin/chromedriver`).
- The Python dependencies listed in `requirements.txt`:
  - `streamlit`
  - `selenium`
  - `pandas`
  - `google-generativeai`
  - `webdriver-manager`

---

## Initial Setup
1. **Clone the repository**
   ```bash
   git clone https://github.com/<your-org>/ListingLens.git
   cd ListingLens
   ```
2. **(Optional) Create a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   ```
3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
4. **Ensure Chrome/Chromium is installed** and that the version matches the ChromeDriver binary your environment provides. On managed platforms (e.g., Streamlit Community Cloud), refer to their documentation for installing extra system packages via `packages.txt`.

---

## Configuring the Google Gemini API Key
ListingLens halts immediately if the `GOOGLE_API_KEY` secret is missing. Provide it via Streamlit secrets or environment variables as follows:

- **Streamlit (recommended):** Create a `.streamlit/secrets.toml` file and add:
  ```toml
  GOOGLE_API_KEY = "your_api_key_here"
  ```
- **Streamlit Community Cloud:** Use the “Secrets” configuration panel to add the same key-value pair.
- **Local environment variable (advanced):** Export `GOOGLE_API_KEY` before launching Streamlit, then read it in `listinglens.py` (if you adapt the code to fall back to environment variables).

Once configured, the Gemini SDK is initialised with `genai.configure(api_key=GOOGLE_API_KEY)`. Any misconfiguration is surfaced in the UI with actionable error messages.

---

## Running the Streamlit App
Launch the interactive interface with:
```bash
streamlit run listinglens.py
```
The command opens a local server (default: http://localhost:8501). In hosted environments, Streamlit exposes the public URL for you.

---

## Using the App
1. **Paste URLs:** Enter one listing URL per line in the text area. Both HTTP and HTTPS schemes are accepted; malformed inputs are reported and skipped.
2. **Start extraction:** Click **“🔍 Extract Details from URLs”**. A spinner, progress bar, and status text reflect the batch progress.
3. **Wait for processing:** Behind the scenes, Selenium loads each page, reveals hidden elements, and collects targeted HTML before Gemini converts it to structured data.
4. **Review results:** Successful entries appear in a table sorted according to the defined column priority (`COLUMN_ORDER`). Missing fields are normalised to `N/A` or `0`.

---

## Output & Downloads
- **Successful results table:** Shows URL, listing title, project name, pricing, area, state, square footage, bedroom/bathroom counts, property type, car parks, floor range, phone number, description, processing time, and any AI error messages.
- **CSV export:** Use the “⬇️ Download Successful Results as CSV” button to export a UTF-8 encoded file ready for spreadsheets or downstream pipelines.
- **Failure summary:** Expand the **“⚠️ View Processing Issues & Errors”** panel to inspect URLs that failed scraping or AI analysis, along with timing metrics and raw error messages when available.

---

## Error Handling & Logs
- The UI surfaces validation warnings, timeouts, and AI parsing issues inline.
- Selenium retries button clicks, logs stale elements, and records WebDriver exceptions with detailed stack traces.
- Structured logs are emitted to the console and, if configured externally, can be redirected to `property_scraper.log` for persistent storage.

---

## Customisation Tips
- **Adjust concurrency:** Update `MAX_CONCURRENT_WORKERS` in `listinglens.py` to control how many URLs are processed simultaneously (default: 5).
- **Extend selectors:** Modify the `target_css_selectors` list to capture additional HTML blocks specific to your target websites.
- **Tweak timeouts:** Tune values such as `PAGE_LOAD_TIMEOUT`, `BUTTON_WAIT_TIMEOUT`, and `POST_CLICK_DELAY` to match the responsiveness of your data sources.
- **Local experimentation:** Use `scraper.py` as a sandbox to iterate on selectors and ChromeDriver settings without running the full Streamlit experience.

---

## Troubleshooting
| Symptom | Likely Cause | Suggested Fix |
|---------|--------------|---------------|
| Immediate Streamlit error stating the API key is missing | `GOOGLE_API_KEY` not set in secrets | Add the key to `.streamlit/secrets.toml` or the Streamlit Cloud Secrets panel. |
| Selenium reports `DevToolsActivePort file doesn't exist` | Chrome/Chromium or ChromeDriver mismatch, insufficient container resources | Ensure compatible versions, or install Chrome/ChromeDriver via `packages.txt` in Streamlit Cloud. |
| All rows show `No relevant HTML content found` | Target selectors fail to match DOM elements after page changes | Inspect the page structure with browser dev tools and update `target_css_selectors`. |
| Gemini response cannot be parsed (`Failed to parse AI response`) | Model returned non-JSON output or rate-limited | Retry later, or add guardrails to re-prompt the model with stricter instructions. |

---

## Support
For product questions or assistance, reach out to **Weldon Tan** at [weldontan.pro@gmail.com](mailto:weldontan.pro@gmail.com).
