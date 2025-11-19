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
- **Intelligent Data Extraction:** Prioritizes structured data sources like `__NEXT_DATA__` script tags and JSON-LD for high-fidelity results, falling back to full-page analysis when necessary to ensure no detail is missed.
- **AI-powered parsing:** Sends the aggregated HTML to the `gemini-2.5-flash` model through the `google-generativeai` SDK to extract a consistent JSON payload containing title, project name, price, location, property details, phone number, and description.
- **Batch processing:** Accepts multiple URLs (one per line) and processes them concurrently (default: 3 workers) with progress bars and status updates so you can monitor large workloads.
- **Result dashboards:** Presents successful extractions in a sortable table and exposes a CSV download button while grouping failures with diagnostic messages for quick follow-up.

---

## System Architecture
| Component | File | Responsibility |
|-----------|------|----------------|
| Streamlit UI & Orchestration | `listinglens.py` | Collects URLs, coordinates multi-threaded processing, renders progress indicators, tables, download buttons, and error panels. |
| Selenium Scraper | `listinglens.py` (`scrape_targeted_sections`) | Configures headless Chromium/ChromeDriver, navigates to listings, performs scripted interactions, and extracts HTML (prioritizing structured data). |
| AI Extraction | `listinglens.py` (`extract_property_details`) | Formats prompts for Gemini, validates JSON responses, enriches results with URL metadata, and captures AI parsing errors. |
| Logging | Console + optional `property_scraper.log` | Emits timestamped diagnostics that mirror the terminal output to aid debugging. |

> **Note:** `scraper.py` is a reference implementation for local experimentation and debugging.

---

## Requirements
- Python 3.10 or higher.
- Google Gemini API access with a valid API key.
- Google Chrome/Chromium and a matching ChromeDriver binary available on the system PATH.
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
4. **Ensure Chrome/Chromium is installed** and that the version matches the ChromeDriver binary your environment provides.

---

## Configuring the Google Gemini API Key
ListingLens halts immediately if the `GOOGLE_API_KEY` secret is missing. Provide it via Streamlit secrets or environment variables as follows:

- **Streamlit (recommended):** Create a `.streamlit/secrets.toml` file and add:
  ```toml
  GOOGLE_API_KEY = "your_api_key_here"
  ```
- **Streamlit Community Cloud:** Use the “Secrets” configuration panel to add the same key-value pair.
- **Local environment variable:** Export `GOOGLE_API_KEY` before launching Streamlit.

Once configured, the Gemini SDK is initialised with `genai.configure(api_key=GOOGLE_API_KEY)`.

---

## Running the Streamlit App
Launch the interactive interface with:
```bash
streamlit run listinglens.py
```
The command opens a local server (default: http://localhost:8501).

---

## Using the App
1. **Paste URLs:** Enter one listing URL per line in the text area.
2. **Start extraction:** Click **“🔍 Extract Details from URLs”**.
3. **Wait for processing:** Selenium loads each page, reveals hidden elements, and collects data.
4. **Review results:** Successful entries appear in a table. Missing fields are normalised to `N/A` or `0`.

---

## Output & Downloads
- **Successful results table:** Shows URL, listing title, project name, pricing, area, state, square footage, bedroom/bathroom counts, property type, car parks, floor range, phone number, description, processing time, and any AI error messages.
- **CSV export:** Use the “⬇️ Download Successful Results as CSV” button.
- **Failure summary:** Expand the **“⚠️ View Processing Issues & Errors”** panel to inspect failures.

---

## Error Handling & Logs
- The UI surfaces validation warnings, timeouts, and AI parsing issues inline.
- Selenium retries button clicks and logs stale elements.
- Structured logs are emitted to the console and `property_scraper.log`.

---

## Customisation Tips
- **Adjust concurrency:** Update `MAX_CONCURRENT_WORKERS` in `listinglens.py` to control how many URLs are processed simultaneously (default: 3).
- **Modify Selectors:** The system defaults to extracting `__NEXT_DATA__` and `application/ld+json`. You can modify `target_css_selectors` in `listinglens.py` if you need to target specific visual elements instead.
- **Tweak timeouts:** Tune values such as `PAGE_LOAD_TIMEOUT`, `BUTTON_WAIT_TIMEOUT`, and `POST_CLICK_DELAY` to match the responsiveness of your data sources.

---

## Troubleshooting
| Symptom | Likely Cause | Suggested Fix |
|---------|--------------|---------------|
| Immediate Streamlit error stating the API key is missing | `GOOGLE_API_KEY` not set | Add the key to `.streamlit/secrets.toml`. |
| Selenium reports `DevToolsActivePort file doesn't exist` | Chrome/Chromium mismatch | Ensure compatible versions. |
| All rows show `No relevant HTML content found` | Page structure changed significantly | Inspect page and update selectors or fallback strategy. |
| Gemini response cannot be parsed | Model returned non-JSON output | Retry or adjust prompt. |

---

## Support
For product questions or assistance, reach out to **Weldon Tan** at [weldontan.pro@gmail.com](mailto:weldontan.pro@gmail.com).

---

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

---

## Future Enhancements
- **In-App Mudah Search:** Future versions will allow users to search for Mudah.my listings directly within the ListingLens interface.
