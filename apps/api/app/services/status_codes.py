STATUS_DEFINITIONS = [
    # ------------------------
    # 0xxxx: Success / Neutral
    # ------------------------
    {
        "cd_std": "000000",
        "cd_name": "SUCCESS",
        "cd_desc": "Request completed successfully with a high-confidence extraction result.",
    },
    {
        "cd_std": "000050",
        "cd_name": "PARTIAL_SUCCESS",
        "cd_desc": "Request completed but some fields are missing, low-confidence, or degraded.",
    },

    # ------------------------
    # 1xxxx: Crawl / scraping
    # ------------------------
    {
        "cd_std": "000100",
        "cd_name": "CRAWL_FAILED",
        "cd_desc": "Generic crawl failure (navigation, page load, or unknown browser error).",
    },
    {
        "cd_std": "000101",
        "cd_name": "NO_CONTENT_EXTRACTED",
        "cd_desc": "Page loaded but no usable content could be extracted (empty or stripped body).",
    },
    {
        "cd_std": "000102",
        "cd_name": "CRAWL_TIMEOUT",
        "cd_desc": "Crawl exceeded the configured timeout before the wait condition was satisfied.",
    },
    {
        "cd_std": "000103",
        "cd_name": "CRAWL_INTERACTION_ERROR",
        "cd_desc": "Crawl failed during page interaction (clicks/JS execution/scrolling).",
    },
    {
        "cd_std": "000104",
        "cd_name": "CRAWL_HTTP_ERROR",
        "cd_desc": "Crawl received a non-2xx HTTP status code from the target URL.",
    },
    {
        "cd_std": "000105",
        "cd_name": "CRAWL_BLOCKED_OR_CAPTCHA",
        "cd_desc": "Crawl appears to be blocked by anti-bot measures, CAPTCHA, or similar protection.",
    },

    # ------------------------
    # 2xxxx: Gemini / LLM API
    # ------------------------
    {
        "cd_std": "000200",
        "cd_name": "GEMINI_CALL_FAILED",
        "cd_desc": "Generic Gemini API failure (network, service, or SDK-level error).",
    },
    {
        "cd_std": "000201",
        "cd_name": "GEMINI_JSON_PARSE_FAILED",
        "cd_desc": "Gemini returned a response that could not be parsed as the expected JSON schema.",
    },
    {
        "cd_std": "000202",
        "cd_name": "GEMINI_RATE_LIMITED",
        "cd_desc": "Gemini request was rejected due to rate limiting or quota exhaustion.",
    },
    {
        "cd_std": "000203",
        "cd_name": "GEMINI_AUTH_FAILED",
        "cd_desc": "Gemini request failed due to invalid or missing authentication credentials.",
    },
    {
        "cd_std": "000204",
        "cd_name": "GEMINI_MODEL_NOT_FOUND",
        "cd_desc": "Requested Gemini model does not exist or is not available to this project.",
    },
    {
        "cd_std": "000205",
        "cd_name": "GEMINI_INVALID_OUTPUT_SCHEMA",
        "cd_desc": "Gemini returned structured output that violates the declared JSON schema.",
    },

    # ------------------------
    # 3xxxx: Config / environment
    # ------------------------
    {
        "cd_std": "000300",
        "cd_name": "CONFIG_ERROR",
        "cd_desc": "Generic configuration error (invalid settings or incompatible options).",
    },
    {
        "cd_std": "000301",
        "cd_name": "CONFIG_MISSING_ENV",
        "cd_desc": "Required environment variable is missing (e.g. GEMINI_API_KEY).",
    },
    {
        "cd_std": "000302",
        "cd_name": "CONFIG_INVALID_ENV_VALUE",
        "cd_desc": "Environment variable is present but has an invalid or unsupported value.",
    },

    # ------------------------
    # 4xxxx: Input / data issues
    # ------------------------
    {
        "cd_std": "000400",
        "cd_name": "INPUT_ERROR",
        "cd_desc": "Generic input error (malformed data or unsupported format).",
    },
    {
        "cd_std": "000401",
        "cd_name": "INPUT_URL_LIST_EMPTY",
        "cd_desc": "No URLs were provided for processing (urls.txt empty or filtered out).",
    },
    {
        "cd_std": "000402",
        "cd_name": "INPUT_URL_INVALID",
        "cd_desc": "One or more URLs are invalid, malformed, or use an unsupported scheme.",
    },

    # ------------------------
    # 5xxxx: System / runtime
    # ------------------------
    {
        "cd_std": "000500",
        "cd_name": "SYSTEM_ERROR",
        "cd_desc": "Generic system/runtime error (unexpected exception in the pipeline).",
    },
    {
        "cd_std": "000501",
        "cd_name": "SYSTEM_IO_ERROR",
        "cd_desc": "Filesystem or I/O operation failed (read/write permissions, missing file, etc.).",
    },
    {
        "cd_std": "000502",
        "cd_name": "SYSTEM_DEPENDENCY_MISSING",
        "cd_desc": "Required library, binary, or runtime dependency is missing or not installed.",
    },

    # ------------------------
    # 9xxxx: Unknown / catch-all
    # ------------------------
    {
        "cd_std": "000999",
        "cd_name": "UNEXPECTED_ERROR",
        "cd_desc": "An unexpected, uncategorised error occurred that does not match other codes.",
    },
]

STATUS_BY_NAME = {row["cd_name"]: row for row in STATUS_DEFINITIONS}
STATUS_BY_CODE = {row["cd_std"]: row for row in STATUS_DEFINITIONS}
