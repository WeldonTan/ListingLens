# ListingLens System Review

## Section A: Architecture Diagram & Components
```
[Next.js Frontend]
        |
        v
[FastAPI Backend] --(Redis broker)-- [Celery Worker]
        |                              |\
        |                              |  \-- [Selenium Grid + Chrome]
        |                              |  \-- [Google Gemini API]
        |                              \-- [PostgreSQL]
        |
   [Qdrant (unused in code)]
```
- **Next.js Frontend**: Client-side dashboard for submitting listing URLs, polling results, deleting history, and exporting CSVs via Axios calls to the backend API.【F:frontend/app/page.tsx†L41-L484】【F:frontend/lib/api.ts†L1-L7】
- **FastAPI Backend**: Hosts REST API for auth and listing CRUD/scrape triggers; wires routers, CORS, and database metadata lifecycle on startup.【F:backend/app/main.py†L1-L32】【F:backend/app/api/v1/endpoints/listings.py†L1-L69】
- **Celery Worker**: Consumes scrape tasks from Redis, drives Selenium to collect HTML, invokes Gemini for AI extraction, and persists results asynchronously to Postgres.【F:backend/app/worker.py†L1-L96】【F:backend/app/services/scraper.py†L1-L115】【F:backend/app/services/gemini.py†L1-L123】
- **PostgreSQL**: Primary relational store for users and listings, configured via SQLAlchemy async engine/session utilities.【F:backend/app/db/session.py†L1-L21】【F:backend/app/models/listing.py†L1-L24】
- **Redis**: Celery broker/backend for task queueing between API and worker containers.【F:backend/app/worker.py†L11-L15】【F:docker-compose.yml†L41-L86】
- **Selenium Grid (hub + Chrome node)**: Headless browser stack used by the worker to render and interact with listing pages before extraction.【F:backend/app/services/scraper.py†L15-L114】【F:docker-compose.yml†L87-L105】
- **Google Gemini API**: LLM invoked for structured field extraction from scraped HTML; configured by env key and guarded with retry logic.【F:backend/app/services/gemini.py†L1-L123】【F:backend/app/core/config.py†L48-L53】
- **Qdrant Vector DB**: Declared in config and docker-compose but currently unused in application code paths.【F:docker-compose.yml†L106-L116】【F:backend/app/core/config.py†L51-L53】

## Section B: Dependency & Ownership Table
| Path / Area | Primary Owner (guess) | Notes on Dependencies & Bus Factor |
| --- | --- | --- |
| `frontend/app` | Frontend team | Depends on `@/lib/api`, UI components, Axios; single-page dashboard suggests low redundancy (bus factor 1-2).【F:frontend/app/page.tsx†L1-L484】 |
| `frontend/components/ui` | Frontend UI/system design | Shared primitives used across dashboard; limited complexity, likely single author.【F:frontend/components/ui/button.tsx†L1-L46】【F:frontend/components/ui/card.tsx†L1-L52】 |
| `frontend/lib` | Frontend platform | API client and utilities used app-wide; small surface but critical for endpoint base URL correctness.【F:frontend/lib/api.ts†L1-L7】 |
| `backend/app/api` | Backend/API team | Routers glue endpoints to services/models; depends on db session, security; bus factor moderate (few files).【F:backend/app/api/v1/endpoints/listings.py†L1-L69】 |
| `backend/app/services` | Data/ML + Infra | Scraper and Gemini integration; heavy external dependencies (Selenium, LLM). Single maintainer risk high.【F:backend/app/services/scraper.py†L1-L115】【F:backend/app/services/gemini.py†L1-L123】 |
| `backend/app/worker.py` | Platform team | Bridges Celery, scraping, Gemini, and DB; central orchestrator with multiple external systems—bus factor risk high.【F:backend/app/worker.py†L1-L96】 |
| `backend/app/db` & `backend/app/models` | Backend persistence | Shared by API and worker; schema definitions and session management underpin all persistence—changes high blast radius.【F:backend/app/models/listing.py†L1-L24】【F:backend/app/db/session.py†L1-L21】 |
| `docker-compose.yml` | DevOps/SRE | Defines all runtime services; edits affect entire stack; likely owned by infra-focused contributor.【F:docker-compose.yml†L1-L116】 |

## Section C: Improvement Backlog
| ID | Title | Area | Est | Risk | Acceptance Criteria |
| --- | --- | --- | --- | --- | --- |
| IM-01 | Harden auth & seed admin user | Security | 1d | M | Add user creation/seed path with hashed password; enforce auth on listing routes; update docs/env for credentials.【F:backend/app/api/v1/endpoints/auth.py†L1-L35】【F:backend/app/api/v1/endpoints/listings.py†L13-L69】 |
| IM-02 | Secret management & env defaults | Security | 1d | M | Move secrets from compose into `.env` with sensible defaults and validation errors when missing (POSTGRES, SECRET_KEY, GOOGLE_API_KEY).【F:docker-compose.yml†L19-L57】【F:backend/app/core/config.py†L22-L55】 |
| IM-03 | Input validation for scrape URLs | Reliability | 1d | L | Validate URLs in `ListingScrapeRequest` with `HttpUrl`, reject duplicates, and cap batch size to prevent queue flooding.【F:backend/app/schemas/listing.py†L1-L36】【F:backend/app/api/v1/endpoints/listings.py†L23-L45】 |
| IM-04 | Idempotent scraping & dedupe | Reliability | 2d | M | Before enqueuing, check DB for existing URL; worker should skip/refresh intelligently to avoid unique constraint collisions on `Listing.url`.【F:backend/app/models/listing.py†L9-L24】【F:backend/app/api/v1/endpoints/listings.py†L23-L45】 |
| IM-05 | Structured logging & tracing | Observability | 2d | M | Standardize structlog config, attach request/task IDs, and forward to console/JSON for both API and worker; ensure Celery logs include task context.【F:backend/app/services/scraper.py†L12-L114】【F:backend/app/services/gemini.py†L1-L123】 |
| IM-06 | Add health/liveness endpoints | Reliability | 1d | L | Expose `/health` on backend checking DB/Redis connectivity and Celery queue ping; used by compose/monitoring.【F:backend/app/main.py†L17-L32】【F:docker-compose.yml†L31-L67】 |
| IM-07 | Rate limiting & abuse controls | Security | 2d | M | Apply per-IP rate limits on scrape and delete endpoints; respond with 429; document limits.【F:backend/app/api/v1/endpoints/listings.py†L23-L69】 |
| IM-08 | Retriable Selenium sessions | Reliability | 2d | M | Add bounded retries/backoff for Selenium failures, surfacing clear error codes; include timeout metrics.【F:backend/app/services/scraper.py†L1-L115】 |
| IM-09 | Async Gemini client & timeout guards | Performance | 2d | M | Offload Gemini call with async/thread executor, add request timeouts and circuit breaker to avoid worker hangs.【F:backend/app/services/gemini.py†L1-L123】 |
| IM-10 | Background polling channel | DevEx | 1d | L | Replace frontend polling with server-sent events or WebSocket for task progress, reducing redundant GETs.【F:frontend/app/page.tsx†L71-L104】 |
| IM-11 | CSV export from backend | Reliability | 1d | L | Provide `/listings/export` endpoint returning CSV to keep schema in one place and avoid browser CSV inconsistencies.【F:frontend/app/page.tsx†L144-L186】 |
| IM-12 | Add Alembic migrations | Reliability | 1d | L | Introduce migrations instead of runtime table creation; document migration workflow in CI/CD.【F:backend/app/main.py†L10-L32】 |
| IM-13 | CI test scaffolding | DevEx | 2d | L | Add minimal backend/worker unit tests and frontend lint/test steps; unskip pytest placeholder in CI workflow.【F:.github/workflows/ci.yml†L1-L52】 |
| IM-14 | Container resource limits | Cost | 1d | L | Set CPU/memory limits in compose for Selenium/worker to prevent local resource exhaustion; tune Chrome `shm_size`.【F:docker-compose.yml†L41-L105】 |
| IM-15 | Qdrant usage cleanup | Cost | 1d | L | Remove unused Qdrant service or implement vector storage feature; update config accordingly to avoid wasted resources.【F:docker-compose.yml†L106-L116】【F:backend/app/core/config.py†L51-L53】 |
| IM-16 | Data retention & purge jobs | Reliability | 2d | M | Add scheduled task (Cron/Celery beat) to purge stale listings and logs; configurable retention window.【F:backend/app/models/listing.py†L9-L24】【F:backend/app/worker.py†L74-L96】 |
| IM-17 | API pagination & filtering | Performance | 1d | L | Implement query params (state, price range) with pagination metadata to reduce payload size for history view.【F:backend/app/api/v1/endpoints/listings.py†L13-L69】 |
| IM-18 | Secure CORS & HTTPS assumptions | Security | 1d | L | Restrict `allow_origins` to configured hosts and document HTTPS requirements for production deployments.【F:backend/app/main.py†L17-L32】【F:backend/app/core/config.py†L9-L20】 |
| IM-19 | Error surface to UI | DevEx | 1d | L | Show toast/error states on scrape failures or deletions instead of silent console logs; include task IDs in UI.【F:frontend/app/page.tsx†L61-L142】 |
| IM-20 | Preflight dependency cache | Performance | 1d | L | Add Docker layer caching for node_modules/pip deps to speed CI builds and local rebuilds.【F:backend/Dockerfile†L1-L20】【F:frontend/Dockerfile†L1-L20】 |

## Section D: Do Not Touch Yet
- **Legacy standalone scraper scripts (`scraper.py`, `constants.py`)**: Unused by current FastAPI/Celery flow; unclear parity with worker pipeline and may carry local-path assumptions—risk of reintroducing regressions if edited casually.【F:scraper.py†L1-L120】【F:constants.py†L1-L64】
- **Selenium Grid tuning**: Chrome node resources and timeouts are tightly coupled to scraping reliability; modifications without load testing could destabilize extraction success.【F:backend/app/services/scraper.py†L1-L115】【F:docker-compose.yml†L87-L105】
- **Gemini prompt/handling**: Prompt currently embedded with specific extraction fields and retry semantics; altering without evaluation could degrade data quality or spike token costs.【F:backend/app/services/gemini.py†L9-L123】
