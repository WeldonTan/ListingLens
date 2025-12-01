import asyncio
import json
import os
import time
import re
import structlog
from dataclasses import dataclass, asdict
from datetime import datetime

from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    CacheMode,
)
from google import genai
from app.services.status_codes import STATUS_BY_NAME

logger = structlog.get_logger()

# ----------------------------------------------------------
# Config
# ----------------------------------------------------------
# Use os.getenv or settings from config.py if available.
# Assuming env vars are set in the environment.
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
DELAY_BEFORE_RETURN_HTML = float(os.getenv("DELAY_BEFORE_RETURN_HTML", "0.5"))
MAX_CONTENT_CHARS = int(os.getenv("MAX_CONTENT_CHARS", "100000"))
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
GEMINI_MAX_ATTEMPTS = int(os.getenv("GEMINI_MAX_ATTEMPTS", "2"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

# ----------------------------------------------------------
# Gemini client
# ----------------------------------------------------------
def configure_gemini_client() -> genai.Client:
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY (or GOOGLE_API_KEY) is not set."
        )
    return genai.Client(api_key=GEMINI_API_KEY)

# ----------------------------------------------------------
# Crawl4AI JS interactions (scroll + show more + show contact)
# ----------------------------------------------------------
def build_js_commands() -> list[str]:
    """
    1. Scroll top -> bottom to trigger lazy loading.
    2. Click all relevant "show more" / "show contact number" / "call"/"whatsapp" buttons.
       We handle multiple such buttons by iterating over them.
    """
    return [
        "window.scrollTo(0, 0);",
        "window.scrollTo(0, document.body.scrollHeight);",
        """
        (function () {
          const buttons = Array.from(
            document.querySelectorAll("button, a[role='button'], div[role='button']")
          );

          const wantShowMore = ["show more"];
          const wantContact = ["show contact number", "show contact", "show phone number"];
          const wantCall = ["call", "whatsapp", "chat"];

          function clickByKeywords(keywords, flagName) {
            buttons.forEach(btn => {
              const txt = (btn.innerText || btn.textContent || "").toLowerCase().trim();
              if (!txt) return;
              if (btn.dataset[flagName]) return;
              if (keywords.some(k => txt.includes(k))) {
                btn.dataset[flagName] = "1";
                try {
                  btn.scrollIntoView({behavior:"instant", block:"center"});
                } catch (e) {}
                btn.click();
              }
            });
          }

          clickByKeywords(wantShowMore, "__clickedShowMore");
          clickByKeywords(wantContact, "__clickedContact");
          clickByKeywords(wantCall, "__clickedCall");
        })();
        """,
    ]

async def fetch_page_text_and_html(
    url: str, crawler: AsyncWebCrawler
) -> tuple[str, str, float]:
    """
    Returns: (page_text_for_gemini, raw_html, crawl_duration_sec)
    """
    url = url.strip()
    if not url:
        raise ValueError("Empty URL")

    js_commands = build_js_commands()

    # Wait until body looks "listing-ish"
    # Optimized: Reduced char count check and simplified wait
    wait_js = (
        "js:() => {"
        "  const txt = (document.body.innerText || '').replace(/\\s+/g, ' ');"
        "  if (txt.length < 300) return false;"
        "  return true;"
        "}"
    )

    run_config = CrawlerRunConfig(
        js_code=js_commands,
        wait_for=wait_js,
        wait_for_timeout=10000,
        delay_before_return_html=DELAY_BEFORE_RETURN_HTML,
        scan_full_page=True,
        cache_mode=CacheMode.BYPASS,
        verbose=True,
    )

    logger.info("scraper.navigate", url=url)
    t0 = time.perf_counter()
    result = await crawler.arun(url=url, config=run_config)
    crawl_duration = time.perf_counter() - t0

    logger.info("scraper.crawled", url=url, success=result.success, status=getattr(result, 'status_code', None))

    if not result.success:
        raise RuntimeError(f"Crawl failed for {url}: {result.error_message}")

    raw_html = result.html or ""
    cleaned_html = result.cleaned_html or ""
    raw_md = getattr(getattr(result, "markdown", None), "raw_markdown", "") or ""
    
    if raw_md:
        page_text = raw_md
    elif cleaned_html:
        page_text = cleaned_html
    else:
        page_text = raw_html

    return page_text, raw_html, crawl_duration

# ----------------------------------------------------------
# Schema & helpers
# ----------------------------------------------------------
FIELD_NAMES = [
    "url",
    "listing_title",
    "project_name",
    "area",
    "state",
    "price",
    "sq_ft",
    "bedrooms",
    "bathrooms",
    "property_type",
    "carpark",
    "floor_range",
    "phone_number",
    "description",
    "tenure",
    "furnishing",
    "completion_year",
]

def empty_record(url: str) -> dict:
    return {k: (url if k == "url" else None) for k in FIELD_NAMES}

def extract_phone_candidates_from_html(raw_html: str) -> list[str]:
    candidates: list[str] = []
    phone_patterns = [
        r"\b01\d[-\s]?\d{3}[-\s]?\d{4}\b",
        r"\b01\d\d{7,8}\b",
        r"\b0\d{1,2}-\d{6,8}\b",
        r"\b6\d{8,11}\b",
    ]
    for pat in phone_patterns:
        for m in re.finditer(pat, raw_html):
            val = m.group(0).strip()
            if val not in candidates:
                candidates.append(val)
    return candidates

# ----------------------------------------------------------
# Meta logging
# ----------------------------------------------------------
@dataclass
class GeminiMeta:
    status_key: str
    status_code: str
    gemini_model: str | None = None
    gemini_attempts: int = 0
    gemini_prompt_tokens: int | None = None
    gemini_response_tokens: int | None = None
    gemini_total_tokens: int | None = None
    gemini_duration_sec: float | None = None
    crawl_duration_sec: float | None = None
    total_duration_sec: float | None = None
    timestamp_utc: str | None = None

def _status_row(status_name: str) -> dict:
    return STATUS_BY_NAME.get(status_name, STATUS_BY_NAME["UNEXPECTED_ERROR"])

def make_meta(
    status_name: str,
    crawl_duration_sec: float | None,
    total_duration_sec: float | None,
    gemini_model: str | None = None,
    attempts: int = 0,
    usage: dict | None = None,
    gemini_duration_sec: float | None = None,
) -> dict:
    row = _status_row(status_name)
    usage = usage or {}
    ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    meta = GeminiMeta(
        status_key=row["cd_name"],
        status_code=row["cd_std"],
        gemini_model=gemini_model,
        gemini_attempts=attempts,
        gemini_prompt_tokens=usage.get("prompt_token_count"),
        gemini_response_tokens=usage.get("candidates_token_count"),
        gemini_total_tokens=usage.get("total_token_count"),
        gemini_duration_sec=gemini_duration_sec,
        crawl_duration_sec=crawl_duration_sec,
        total_duration_sec=total_duration_sec,
        timestamp_utc=ts,
    )
    return asdict(meta)

# ----------------------------------------------------------
# Gemini extraction
# ----------------------------------------------------------
def extract_with_gemini(
    client: genai.Client,
    url: str,
    page_text: str,
    raw_html: str,
    crawl_duration_sec: float,
) -> tuple[dict, dict]:
    t0_total = time.perf_counter()
    phone_candidates = extract_phone_candidates_from_html(raw_html)
    content = page_text[:MAX_CONTENT_CHARS]
    hints_block = (
        "PHONE CANDIDATES (from full HTML, may include numbers from scripts, links, or hidden widgets):\n"
        f"{phone_candidates}\n\n"
    )

    base_prompt = f"""
You are an assistant that extracts structured data from a SINGLE property listing page on mudah.my.

Use BOTH the page content and the phone candidates list below.
The phone candidates may come from JavaScript, links (e.g. wasap.my/6012...), or other hidden parts of the HTML.

Rules for phone_number:
- You MUST search for phone numbers anywhere in the page, including:
  * main description text
  * "Contact" widgets
  * WhatsApp / tel: links
  * any other visible or hidden text in the HTML
- If there are both masked and full numbers (e.g. "017323****" and "0173238055"),
  you MUST choose the full digit number (0173238055).
- Prefer a single, Malaysian-style phone number (with or without country code).
- You may use the PHONE CANDIDATES list to resolve masked numbers.
- If you only see masked phone numbers (with asterisks) and NO full digit candidate at all,
  then you may return the masked number like "017323****".
- If genuinely no phone number is present anywhere, set phone_number to null.
- Never invent or guess digits that do not appear on the page.

General field rules:
- Extract ONLY what is clearly supported by the content.
- Prefer information specific to THIS listing, not generic area/project blurbs.
- If a field is not clearly present, set it to null.
- Do not hallucinate values.

{hints_block}
Here is the page content (after scrolling and clicking 'show more' and 'Show contact number'):

---------------- PAGE CONTENT START ----------------
{content}
---------------- PAGE CONTENT END ----------------
"""

    response_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "listing_title": {"type": ["string", "null"]},
            "project_name": {"type": ["string", "null"]},
            "area": {"type": ["string", "null"]},
            "state": {"type": ["string", "null"]},
            "price": {"type": ["number", "null"]},
            "sq_ft": {"type": ["number", "null"]},
            "bedrooms": {"type": ["number", "null"]},
            "bathrooms": {"type": ["number", "null"]},
            "property_type": {"type": ["string", "null"]},
            "carpark": {"type": ["number", "null"]},
            "floor_range": {"type": ["string", "null"]},
            "phone_number": {"type": ["string", "null"]},
            "description": {"type": ["string", "null"]},
            "tenure": {"type": ["string", "null"]},
            "furnishing": {"type": ["string", "null"]},
            "completion_year": {"type": ["number", "null"]},
        },
        "required": ["url"],
    }

    config = {
        "response_mime_type": "application/json",
        "response_json_schema": response_schema,
    }

    attempts = 0
    last_error: Exception | None = None
    usage: dict | None = None
    gemini_duration: float | None = None

    while attempts < GEMINI_MAX_ATTEMPTS:
        attempts += 1
        logger.info("gemini.attempt", url=url, attempt=attempts)
        t0 = time.perf_counter()
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=base_prompt,
                config=config,
            )
            gemini_duration = time.perf_counter() - t0
            usage_meta = getattr(response, "usage_metadata", None)
            if usage_meta:
                usage = {
                    "prompt_token_count": getattr(usage_meta, "prompt_token_count", None),
                    "candidates_token_count": getattr(usage_meta, "candidates_token_count", None),
                    "total_token_count": getattr(usage_meta, "total_token_count", None),
                }

            raw = (response.text or "").strip()
            data = json.loads(raw)
            record = empty_record(url)
            for k in FIELD_NAMES:
                if k == "url":
                    record[k] = url
                else:
                    val = data.get(k, None)
                    # Helper to clean numeric fields if they come as strings
                    if k in ["price", "sq_ft", "bedrooms", "bathrooms", "carpark", "completion_year"] and isinstance(val, str):
                        # Remove everything except digits and dots
                        val_clean = re.sub(r"[^\d.]", "", val)
                        try:
                            if val_clean:
                                if "." in val_clean:
                                    val = float(val_clean)
                                else:
                                    val = int(val_clean)
                            else:
                                val = 0
                        except ValueError:
                            val = 0
                    
                    record[k] = val

            total_duration = time.perf_counter() - t0_total
            meta = make_meta(
                status_name="SUCCESS",
                crawl_duration_sec=crawl_duration_sec,
                total_duration_sec=total_duration,
                gemini_model=GEMINI_MODEL,
                attempts=attempts,
                usage=usage,
                gemini_duration_sec=gemini_duration,
            )
            return record, meta

        except Exception as e:
            last_error = e
            logger.warning("gemini.error", url=url, error=str(e), attempt=attempts)
            continue

    total_duration = time.perf_counter() - t0_total
    logger.error("gemini.failed", url=url, error=str(last_error))
    meta = make_meta(
        status_name="GEMINI_CALL_FAILED",
        crawl_duration_sec=crawl_duration_sec,
        total_duration_sec=total_duration,
        gemini_model=GEMINI_MODEL,
        attempts=attempts,
        usage=usage,
        gemini_duration_sec=gemini_duration,
    )
    return empty_record(url), meta

# ----------------------------------------------------------
# Main Exported Function
# ----------------------------------------------------------
async def scrape_and_extract_listing(url: str) -> dict:
    logger.info("scraper.start", url=url)
    
    # Initialize client
    try:
        client = configure_gemini_client()
    except Exception as e:
        logger.error("scraper.init_error", error=str(e))
        return {"url": url, "error": str(e)}

    browser_conf = BrowserConfig(
        headless=HEADLESS,
        verbose=True,
        viewport_width=1280,
        viewport_height=720,
    )

    try:
        async with AsyncWebCrawler(config=browser_conf) as crawler:
            try:
                page_text, raw_html, crawl_duration = await fetch_page_text_and_html(url, crawler)
            except Exception as e:
                logger.error("scraper.crawl_error", url=url, error=str(e))
                meta = make_meta(
                    status_name="CRAWL_FAILED",
                    crawl_duration_sec=None,
                    total_duration_sec=None,
                    gemini_model=GEMINI_MODEL,
                    attempts=0,
                    usage=None,
                    gemini_duration_sec=None,
                )
                rec = empty_record(url)
                rec["meta"] = meta
                # Include error message in return for worker to see
                rec["error"] = str(e)
                return rec

            record, meta = extract_with_gemini(client, url, page_text, raw_html, crawl_duration)
            record["meta"] = meta
            
            logger.info("scraper.complete", url=url, status=meta['status_key'])
            return record

    except Exception as e:
        logger.error("scraper.system_error", url=url, error=str(e))
        return {"url": url, "error": str(e)}

async def generate_listing_content(listing_data: dict, instruction: str) -> str:
    """
    Generate content for a listing using Gemini.
    """
    try:
        client = configure_gemini_client()
        
        prompt = f"""
You are a professional real estate copywriter.
Instruction: {instruction}

Listing Details:
{json.dumps(listing_data, indent=2)}

Write a compelling description or content based on the instruction.
Keep it under 1000 words.
Do not include any preamble or markdown code blocks (unless requested).
Just return the text.
"""
        
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        
        return (response.text or "").strip()
    except Exception as e:
        logger.error("gemini.generate_error", error=str(e))
        return f"Error generating content: {str(e)}"
