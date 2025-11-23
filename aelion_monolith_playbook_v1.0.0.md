# Aelion Systems — Monolith Engineering Playbook (AI‑Optional)
**Version:** v1.0.0  
**Audience:** Engineering, Product, SRE, Security at Aelion Systems  
**Scope:** Company‑wide standards for building, operating, and scaling **monolithic** applications.  
**Applies To:** Every monolith project (with or without LLM/AI).  
**Status:** Adopted

---

## Table of Contents
1. [Strategic Context & Principles](#1-strategic-context--principles)
2. [Architecture & Framework](#2-architecture--framework)
3. [Configuration & Secrets](#3-configuration--secrets)
4. [API Contract & Integration Standards](#4-api-contract--integration-standards)
5. [Data Modeling & Access](#5-data-modeling--access)
6. [Frontend Standards](#6-frontend-standards-nextjs)
7. [Security & Compliance](#7-security--compliance)
8. [Observability & SRE](#8-observability--sre)
9. [CI/CD & Developer Experience](#9-cicd--developer-experience-dx)
10. [Testing Strategy](#10-testing-strategy)
11. [Data Lifecycle, Backups & DR](#11-data-lifecycle-backups--dr)
12. [Feature Delivery & Rollout](#12-feature-delivery--rollout)
13. [Intelligence & RAG (Optional)](#13-intelligence--rag-optional)
14. [Performance Engineering](#14-performance-engineering)
15. [Administrative Operations](#15-administrative-operations)
16. [Roadmap to Production](#16-roadmap-to-production-phased)
17. [Templates & Boilerplate](#17-templates--boilerplate)
18. [Glossary](#18-glossary)
19. [Checklists](#19-checklists)
20. [Changelog](#20-changelog)

---

## 1) Strategic Context & Principles
### 1.1 Purpose
Deliver enterprise‑grade monoliths that are **fast to ship**, **safe by default**, and **easy to operate**, while allowing an **AI‑optional** path using the same architectural seams.

### 1.2 Core Principles
1. **Backend as Source of Truth.** API contracts defined in Python (Pydantic) and exported to the frontend (OpenAPI → TypeScript).  
2. **Modular Inside, Monolith Outside.** Logical modules (Auth, Data, Intelligence) live in one process group for velocity.  
3. **Guardrails over Guidelines.** Provide defaults (linting, security headers, RLS) that are hard to turn off.  
4. **AI‑Optionalization.** A stable `IntelligenceEngine` protocol enables LLM on/off without forking product code.  
5. **Operational Excellence.** SLOs, golden signals, runbooks, and cost budgets are first‑class.

### 1.3 Standard Technology Inventory
The following tools are the **mandatory** baseline for all new projects.

| Category | Tool / Library | Purpose | Stack Domain |
|---|---|---|---|
| **Frontend** | Next.js 14+ (App Router) | Server-Side Rendering, Routing, UI Framework | Frontend |
| **UI Library** | Tailwind CSS + shadcn/ui | Styling and Accessible Components | Frontend |
| **Backend** | FastAPI (Python 3.11+) | High-performance Async API | Backend |
| **Database** | PostgreSQL 16 | Primary Relational Data Store | Backend |
| **ORM** | SQLAlchemy 2.0 (Async) | Database Abstraction & Query Building | Backend |
| **Migrations** | Alembic | Database Schema Version Control | Backend |
| **Cache & Queue** | Redis 7 | Caching, Rate Limiting, Message Broker | Backend |
| **Worker** | Arq | Async Job Processing (Python) | Backend |
| **Object Store** | MinIO (Local) / S3 (Prod) | File Storage (User uploads, artifacts) | Backend |
| **Vector Store** | Qdrant | Semantic Search Engine (RAG) | Backend |
| **LLM** | Google Gemini API / Vertex | Generative AI Model (Optional) | Backend |
| **Telemetry** | OpenTelemetry | Tracing, Metrics, Logs standard | Shared |
| **Linter/Fmt** | Ruff (Python), Biome/ESLint (JS) | Code Quality & Formatting | Shared |
| **Infrastructure** | Docker Compose | Local Orchestration | DevOps |

---

## 2) Architecture & Framework
### 2.1 Recommended Pattern: Modular Monolith with Service Layer
We adopt a **Service-Layer Pattern** within a **Modular Monolith**. This provides clear separation of concerns while keeping the codebase unified.

- **Presentation Layer (Routes):** `apps/api/app/api/v1/`
  - **Role:** Handle HTTP requests, parse params, enforce permissions, call Services.
  - **Rule:** No business logic here. Returns Pydantic Schemas.
- **Service Layer (Business Logic):** `apps/api/app/services/`
  - **Role:** The brain. Orchestrates DB transactions, calls external APIs, enqueues jobs.
  - **Rule:** Framework agnostic. Should not know about HTTP requests directly.
- **Data Access Layer (Models):** `apps/api/app/models/` & `apps/api/app/db/`
  - **Role:** Define DB tables (SQLAlchemy).
  - **Rule:** Accessed only by Services (mostly).
- **Interface Layer (Schemas):** `apps/api/app/schemas/`
  - **Role:** Data Transfer Objects (DTOs) using Pydantic.
  - **Rule:** Defines the contract between API and Frontend.

### 2.2 Logical Modules
```
[Web (Next.js)] ⇄ [FastAPI Gateway] ⇄ [Services Layer]
                                       ├─ Auth Module
                                       ├─ Data/Content Module
                                       ├─ Intelligence Module (AI)
                                       ├─ Audit Module
                                       └─ Worker Module
Stores: Postgres (primary), Redis (cache/queues), MinIO/S3, Qdrant (optional)
```

### 2.3 Service Responsibilities
- **Frontend (Next.js):** Renders UI, handles client-side state, manages auth flows (login/refresh), and uploads files directly to S3/MinIO via presigned URLs.
- **Backend API (FastAPI):** Provides REST endpoints, request validation, RLS enforcement, generates presigned URLs, and coordinates async jobs.
- **Worker (Arq):** Executes background tasks (email sending, embeddings, report generation) and periodic housekeeping.
- **Uploads:** API issues presigned URLs; backend MUST NOT proxy large files.
- **S3 in prod, MinIO locally;** identical flow.
- **Data Stores:**
  - **PostgreSQL:** System of record.
  - **Redis:** Cache (volatile) and Queue (persistent).
  - **MinIO/S3:** Durable object storage (files, artifacts).
  - **Qdrant:** Vector search for RAG.

### 2.3.1 Error Handling Strategy
- **Service Layer Exceptions:** Services MUST raise specific, typed exceptions (e.g., `UserNotFoundError`, `InsufficientFundsError`) rather than returning `None` or `False`.
- **API Exception Handlers:** The presentation layer (`apps/api/app/main.py`) MUST register global exception handlers to catch these service exceptions and map them to appropriate HTTP Status Codes (e.g., `UserNotFoundError` -> 404).
- **Logging:** All exceptions in the 5xx range MUST be logged with full stack traces; 4xx exceptions should be logged as warnings or info.

### 2.4 Monorepo Structure
```
apps/
  web/                   # Frontend Application
    app/                 # Next.js App Router
    components/          # React Components (ui/, shared/)
    lib/                 # Utilities, fetch wrappers
    types/               # TS Definitions
  api/
    app/
      api/v1/endpoints/  # Presentation Layer (Routes)
      services/          # Business Logic Layer (Services)
      models/            # Data Layer (SQLAlchemy Models)
      schemas/           # Interface Layer (Pydantic Schemas)
      core/              # Config, Security, Telemetry
      worker/            # Background Jobs
    alembic/             # Migrations
    main.py              # Entrypoint
infra/                   # Docker, Terraform, Helm
scripts/                 # Dev tooling

> **Single-image runtime note:** We build Next.js (apps/web) with output: 'standalone' and package it alongside FastAPI (apps/api) into one Docker image. A small process manager (e.g., supervisord) runs both processes at runtime. Local development remains Docker Compose with Postgres/Redis/MinIO.
```

### 2.5 Architectural Risks & Mitigations
- **Database Connection Storms:** MUST use connection pooling (e.g., PgBouncer) in production; limit concurrency in local/dev. When App Runner scales instances, use RDS Proxy or PgBouncer to pool connections.
- **Distributed Monolith Trap:** Avoid splitting services until organizational boundaries dictate it. Keep calls in-process.
- **Queue Durability:** Redis MUST be configured with persistence (AOF/RDB) or use a managed queue service if strictly required for critical jobs.
- **Large File Handling:** Backend MUST NOT proxy files. Use presigned URLs for direct client-to-bucket transfer.
- **Cost spikes:** cache hot reads (Redis), paginate, and avoid N+1 calls.
- **Security:** keep security headers, input validation, and least-privileged IAM.

---

## 3) Configuration & Secrets
### 3.1 Principles
- **Strict Separation:** Code is versioned; Config varies by deployment (env vars).
- **No Defaults for Secrets:** The application MUST crash at startup if critical secrets (DB password, API keys) are missing.
- **Namespaces:** Use distinct prefixes for clarity (e.g., `APP_`, `REDIS_`, `AWS_`).

### 3.2 Standard Variables
| Variable | Description |
|---|---|
| `ENV` | `local`, `staging`, `production` |
| `API_PORT` | Service listen port |
| `DATABASE_URL` | Full connection string (async driver) |
| `REDIS_URL` | Cache endpoint |
| `REDIS_QUEUE_URL` | Queue endpoint (separate DB index recommended) |
| `S3_ENDPOINT`, `S3_BUCKET` | Object storage config |
| `JWT_SECRET`, `JWT_ALGO` | Auth signing material |
| `QDRANT_URL`, `QDRANT_KEY` | Vector DB connection |

### 3.3 Security Notes
- **Local:** Use `.env` files (gitignored).
- **Prod secrets source:** AWS Secrets Manager.
- **At deploy, map secrets to container environment in App Runner:**
  - `DATABASE_URL`, `REDIS_URL`, `JWT`/crypto keys, third-party tokens
- **Never commit secrets;** no default secret values in code.
- **Rotation:** Support key rotation for JWT and API credentials without downtime.

---

## 4) API Contract & Integration Standards
### 4.1 Conventions
- **Base path:** `/api/v1`  
- **Headers:** `X-Request-Id` (correlation), `X-RateLimit-*` (limits), `Deprecation` (if applicable)  
- **Error envelope (MUST):**
```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Record not found",
    "request_id": "req_01H...",
    "hint": "Check id or permissions",
    "details": { "resource": "document", "id": "abc123" }
  }
}
```
- **Idempotency:** Clients send `Idempotency-Key` for POST/PUT/PATCH/DELETE.  
- **Pagination:** Cursor‑based `?cursor=` + `next_cursor` in responses.  
- **Versioning & Deprecation:** 90‑day window with headers + CHANGELOG.

### 4.1.1 Standard HTTP Status Codes
- **200 OK:** Standard success.
- **201 Created:** Resource creation success (MUST return Location header).
- **204 No Content:** Success with no body (e.g., DELETE).
- **400 Bad Request:** Client error (validation failed).
- **401 Unauthorized:** Authentication required/failed.
- **403 Forbidden:** Authenticated but permissions denied.
- **404 Not Found:** Resource does not exist.
- **422 Unprocessable Entity:** Pydantic validation error.
- **429 Too Many Requests:** Rate limit exceeded.
- **500 Internal Server Error:** Unhandled backend exception.

### 4.2 Middleware (Request ID & JSON logs)
```python
# apps/api/app/core/middleware.py
import uuid, time, json, logging
from starlette.middleware.base import BaseHTTPMiddleware
log = logging.getLogger("api")

class RequestContext(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        rid = request.headers.get("x-request-id") or f"req_{uuid.uuid4().hex[:12]}"
        start = time.perf_counter()
        response = await call_next(request)
        dur_ms = int((time.perf_counter() - start) * 1000)
        response.headers["X-Request-Id"] = rid
        log.info(json.dumps({
            "event":"http_request","rid":rid,"path":request.url.path,
            "method":request.method,"status":response.status_code,"dur_ms":dur_ms
        }))
        return response
```

### 4.3 Rate Limiting (per‑org)
```python
# apps/api/app/core/ratelimit.py
import time, aioredis
WINDOW, LIMIT = 60, 600  # 600 req/min/org
async def is_limited(redis: aioredis.Redis, org_id: str) -> bool:
    key = f"rate:{org_id}:{int(time.time()//WINDOW)}"
    count = await redis.incr(key)
    if count == 1: await redis.expire(key, WINDOW+5)
    return count > LIMIT
```

### 4.4 Type Sync
```bash
# scripts/sync-types.sh
set -euo pipefail
echo "Generating OpenAPI Spec…"
curl http://localhost:8000/openapi.json > infra/openapi/openapi.json
echo "Generating TS types…"
npx openapi-typescript infra/openapi/openapi.json -o apps/web/types/api.d.ts
```

---

## 5) Data Modeling & Access
- **DTOs (Pydantic) vs ORM (SQLAlchemy) separation (MUST).**  
- **RLS (MUST) with per‑request `app.org_id` (MUST).**  
- **Migrations:** Alembic autogen → review → upgrade; no manual DDL in prod.
- **Design:** Normalize core entities; use indices for frequent filters; avoid premature sharding.

### 5.1 Naming Conventions
- **Tables:** Plural, snake_case (e.g., `users`, `order_items`).
- **Columns:** snake_case (e.g., `created_at`, `is_active`).
- **Foreign Keys:** `noun_id` (e.g., `user_id`, `organization_id`).
- **Indexes:** `ix_<table>_<column>` (e.g., `ix_users_email`).

**RLS Template**
```sql
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
CREATE POLICY org_isolation ON documents
  USING (org_id = current_setting('app.org_id')::uuid);
```

**DTO Example**
```python
# apps/api/app/schemas/document.py
from pydantic import BaseModel
class DocumentCreate(BaseModel):
    name: str
    dataset_id: str
    content_type: str
class DocumentOut(BaseModel):
    id: str
    name: str
    dataset_id: str
    size_bytes: int
    created_at: str
```

---

## 6) Frontend Standards (Next.js)
### 6.1 Design System: Google‑like Blue/Black/White
```css
/* globals.css */
:root {
  --background: 0 0% 100%;
  --foreground: 222 47% 11%;
  --primary: 217 91% 60%;
  --primary-foreground: 0 0% 100%;
  --muted: 210 40% 96%;
  --muted-foreground: 215 16% 47%;
  --border: 214 32% 91%;
  --ring: 217 91% 60%;
  --radius-sm: .25rem;
  --radius-md: .5rem;
  --radius-lg: .75rem;
  --radius-full: 9999px;
}
.dark {
  --background: 222 47% 6%;
  --foreground: 210 40% 98%;
  --muted: 217 33% 17%;
  --border: 217 33% 17%;
}
```

- **Typography:** Inter/Roboto; base 14px; weight 500 for labels.  
- **Components:** Cards (bordered), pill buttons, input focus ring = primary.  
- **Patterns:** Omnibox at top; collapsible sidebar; hover/active states in blue (no greys).  
- **A11y:** WCAG 2.2 AA, keyboard‑first, 4.5:1 contrast, skip links.
- **Iconography:** Lucide React is the standard icon set.

### 6.2 State Management & Fetching
- **Server State:** Use React Server Components (RSC) for initial data fetch.
- **Client State:** Use `zustand` for global client stores (e.g., sidebar state, user preferences). Avoid Redux.
- **Mutations:** Use Server Actions for form submissions and data mutations.
- **Data Fetching:** Use `fetch` with native caching tags in RSC; use `SWR` or `TanStack Query` for client-side polling or revalidation if needed.

### 6.3 Runtime & Caching
- Sensitive logic on Node runtime; edge runtime for safe suggestions only.  
- `Vary: Authorization` and `Cache-Control: no-store` for user data.  
```ts
export const dynamic = 'force-dynamic'
export async function GET() {
  return new Response(JSON.stringify({ ok: true }), {
    headers: { 'Cache-Control': 'no-store', 'Vary': 'Authorization' }
  })
}
```

### 6.4 Next.js runtime & caching
- **Runtime:** Node on App Runner (default).
- **Build:** output: 'standalone' for container packaging.
- **Revalidation/ISR:** supported; set revalidate per route.
- **Headers:** keep `Cache-Control: no-store` for user-specific data; `Vary: Authorization` where applicable.
- **Env:** expose only safe `NEXT_PUBLIC_*` at build time.

---

## 7) Security & Compliance
### 7.1 AuthN/Z
- OAuth2 + JWT RS256; **Access 15m**, **Refresh 7d** with rotation.  
- **Revocation:** Denylist for compromised tokens stored in Redis with TTL.
- RBAC roles: owner, admin, analyst, viewer; ABAC via dataset tags.  
- Admin actions require re‑auth + reason + audit entry.

### 7.2 AppSec Controls (MUST)
- Strict CSP, HSTS, `frame-ancestors 'none'`, `nosniff`, `no-referrer`.  
- Upload validation: magic numbers, AV scan, size caps, sandboxed parsing.  
- HTML/LLM output sanitization (whitelist), output encoding everywhere.  
- Dependency hygiene: SBOM (Syft), scan (Trivy), signed images where supported.

**Next.js security middleware**
```ts
import { NextResponse } from 'next/server'
export function middleware() {
  const res = NextResponse.next()
  res.headers.set('Strict-Transport-Security', 'max-age=31536000; includeSubDomains; preload')
  res.headers.set('X-Frame-Options', 'DENY')
  res.headers.set('X-Content-Type-Options', 'nosniff')
  res.headers.set('Referrer-Policy', 'no-referrer')
  res.headers.set('Permissions-Policy', 'geolocation=(), microphone=()')
  return res
}
```

### 7.3 Audit & Access Reviews
- Append‑only `audit_logs` with `actor_id, org_id, action, resource, ip, ua, ts, rid`.  
- Quarterly access reviews; least privilege for prod; break‑glass with JIT.

### 7.4 Compliance Starter (SOC2/ISO)
- Controls mapping doc per product: **access control, change mgmt, backups/DR, monitoring, incident response**.  
- Evidence: CI logs, access reviews, backup reports, on‑call rota, runbooks.

---

## 8) Observability & SRE
### 8.1 Telemetry
- **OpenTelemetry** on API, DB, Redis, workers; export to Datadog/OTel collector.  
- Golden signals: latency, error rate, saturation, traffic; queue depth for workers.  
```python
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
def setup_otel(app, engine):
    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
    RedisInstrumentor().instrument()
```

### 8.2 SLOs & Budgets
- Availability **99.9%/mo**; latency P95 < 400ms; AI TTFT < 800ms (if enabled).  
- Burn alerts at **2%/h** (page) and **5%/h** (escalate).
- **Sample Alerts:**
  - API 5xx > 1% over 5 min.
  - Queue backlog > 2 min processing time.
  - DB CPU > 85%.

### 8.3 Runbooks & Incident Response
- **Severity Levels:**
  - **SEV-1 (Critical):** Data loss, full outage. Response < 15m.
  - **SEV-2 (High):** Major feature broken. Response < 1h.
  - **SEV-3 (Moderate):** Minor bug/annoyance.
- **Key Runbooks:**
  - **Startup:** Ensure dependencies up, apply migrations, seed data.
  - **Deploy:** Build, test, migrate (locking), deploy, smoke test.
  - **Rollback:** Revert app version; apply down migrations ONLY if data-safe.
  - **Backup/Restore:** Test PITR recovery quarterly.
  - **Incident:** Triage (logs/metrics) -> Mitigate -> Validate -> Post-Mortem.

### 8.4 One switch (pause/resume) & Operations
- **One switch (pause/resume):** App Runner allows pause and resume of the service for cost control.
- **Databases:** should remain running; keep small instance class for staging/dev.
- **Logs & metrics:** App Runner streams to CloudWatch by default.
- **OTel (optional):** can be added for traces; keep golden signals dashboards and SLOs (availability, latency, error rate).
- **Budgets & alarms:** create AWS Budgets + CloudWatch alarms early.

---

## 9) CI/CD & Developer Experience (DX)
- **DX Standard:** Repository MUST support a single command to start (e.g., `make up`) and test (`make test`).
- **Trunk‑based**, Conventional Commits, Semantic Versioning.  
- **Pre‑commit:** ruff, black, mypy, bandit, detect‑secrets, eslint, prettier.  
- **Pipeline (main branch):**
  1. **Build & test:** unit → integration (compose) → contract/fuzz → smoke (pre-deploy)
  2. **Build Docker image** (single image) and scan
  3. **Push to ECR**
  4. **DB migrations:** run Alembic upgrade head against target env
  5. **Deploy to AWS App Runner:** start-deployment for the service
  6. **Post-deploy smoke test:** public /healthz; rollback to previous image on failure
- **Rollback:** redeploy previous ECR image tag to App Runner.
- **Preview envs** per PR with seeded synthetic data.

### Minimal GitHub Actions skeleton
```yaml
name: ci-cd
on: { push: { branches: [main] } }
jobs:
  build-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - run: pnpm i && pnpm -C apps/web build
      - run: docker build -t $IMAGE_TAG .
      # run tests, scans...
  deploy:
    needs: build-test
    runs-on: ubuntu-latest
    steps:
      - name: Login & Push to ECR
        run: |
          # aws ecr get-login-password | docker login ...
          docker tag $IMAGE_TAG $ECR_REPO:$GIT_SHA
          docker push $ECR_REPO:$GIT_SHA
      - name: Alembic migrate
        run: python -m alembic upgrade head
      - name: App Runner deploy
        run: aws apprunner start-deployment --service-arn $SERVICE_ARN
      - name: Smoke test
        run: curl -fsS https://YOUR_APP_URL/healthz
```
- **Caching:** CI pipelines MUST cache `node_modules` (npm/pnpm), `.venv` (poetry/uv), and `.mypy_cache` to accelerate feedback loops.

### 9.1 Local Development
- Use Docker Compose to run Postgres, Redis, and the app in live-reload mode.
- Keep secrets in `.env` (gitignored). Same names exist in prod via Secrets Manager.
- Presigned uploads: browser → MinIO (local) using the same API flow as S3 (prod).

**Optional dev docker-compose.yml snippet**
```yaml
services:
  db:
    image: postgres:16
    environment: { POSTGRES_PASSWORD: postgres }
    ports: ["5432:5432"]
  redis:
    image: redis:7
    ports: ["6379:6379"]
  app:
    build: .
    command: >
      bash -lc "pnpm dev:web & uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000"
    env_file: .env
    ports: ["3000:3000","8000:8000"]
    volumes: [".:/workspace"]
```

---

## 10) Testing Strategy
- **Unit:** services/utils (≥80% in core modules).  
- **Contract:** generated clients from OpenAPI; schemathesis fuzzing.  
- **Integration:** real Postgres/Redis/Qdrant in compose.  
- **E2E:** Playwright for upload/search/answer; auth flows.  
- **Load/Soak:** k6 for hot paths, nightly soak for memory leaks.

### 10.1 Testing Implementation Details
- **Fixtures:** Use `pytest-asyncio` with `scope="function"` fixtures to wrap each test in a database transaction that rolls back after execution. This ensures test isolation.
- **Factories:** Use `polyfactory` or `factory_boy` to generate deterministic test data for Pydantic models and SQLAlchemy ORM models.
- **Mocks:** Use `unittest.mock` or `pytest-mock` only for external services (e.g., S3, Stripe, Email). NEVER mock the database; use the Dockerized Postgres instance.

---

## 11) Data Lifecycle, Backups & DR
- **Targets:** RPO ≤ 5m, RTO ≤ 30m.  
- **Backups:** Postgres PITR (WAL‑G→S3), hourly Qdrant snapshots (if used), S3 versioning/lifecycle.  
- **Retention:** tenant TTLs; RTBF workflow; crypto‑erasure keys per tenant (optional).  
- **Lineage:** dataset id, file version, parser version in metadata.

---

## 12) Feature Delivery & Rollout
- Feature flags; dark launch; % rollout; **kill switch** per feature.  
- Remove stale flags post‑GA.  
- Release notes and deprecation notices required for breaking changes.

---

## 13) Intelligence & RAG (Optional)
### 13.1 Pipeline (AI mode)
1) **Ingest:** upload → MinIO → worker picks file id.  
2) **Parse:** PyPDF/LlamaParse; chunk ~1k tokens/overlap 100.  
3) **Embed:** text‑embedding‑004; Qdrant upsert with `{ org_id, file_id, dataset }`.  
4) **Retrieve:** hybrid vector + BM25; payload filters for RBAC.  
5) **Generate:** `gemini-3-pro-preview` with structured JSON output.  
6) **Safety:** prompt injection guards; PII redaction; HTML sanitization.

### 13.2 Protocol & Implementation
```python
# apps/api/app/services/intelligence.py
from typing import Protocol, Optional

class IntelligenceEngine(Protocol):
    async def answer(self, prompt: str, context: Optional[str] = None) -> str: ...

class NullEngine:
    async def answer(self, prompt: str, context: Optional[str] = None) -> str:
        return "AI disabled. Showing curated results and keyword matches."
```

### 13.3 Governance & Evaluation
- Prompt registry with owner, changelog, tests; JSON‑schema‑enforced outputs.  
- Metrics: P@k/Recall@k/MRR; Faithfulness (<2% hallucination); nightly regression.

### 13.4 Cost & Fallbacks
- Tiered models (flash → pro); per‑tenant token budgets; circuit breakers; fallback to **NullEngine**.

---

## 14) Performance Engineering
- **Web:** RSC boundaries; streaming via `ReadableStream`; compact UI density; avoid unnecessary client components.  
- **API:** async I/O, statement timeouts, pool sizing, N+1 detection, prepared statements.  
- **DB:** essential indexes, partial indexes, autovacuum tuning.  
- **Cache:** positive + negative caching; short TTLs for error paths.  
- **Vectors (AI):** tune HNSW for recall/latency targets.

---

## 15) Administrative Operations
- **Tenant Provisioning:** org create → seed roles → set `app.org_id`.  
- **Tenant Deletion:** soft delete → retention window → hard delete → wipe vectors/files (AI).  
- **SSO:** OIDC/SAML, metadata import, SCIM (optional).  
- **Env Bootstrap:** Makefile targets for compose up, db migrate, seed.

---

## 16) Roadmap to Production (Phased)
### Phase A — Harden Local & Create Staging

#### Acceptance Summary Checklist
- **Local:** `.env` configured, docker compose up, tests pass.
- **CI:** pipeline runs tests → builds image → scans → pushes to ECR → migrates DB → App Runner deploy → smoke test.
- **Staging:** week-long stable demo, backup/restore drill.
- **Prod (later):** Multi-AZ RDS, pooling, WAF/CDN, blue/green capable.

**Goals:** Mirror local architecture in the cloud; enable demos.
- **Deliverables:**
  - Cloud env with container orchestration (API, Worker).
  - Managed Postgres, Redis, Object Storage.
  - CI/CD pipeline (Build -> Test -> Migrate -> Deploy).
  - Basic observability (Logs, Dashboards).

#### Runtime (Default): AWS App Runner
We deploy the entire monolith as a single Docker image to AWS App Runner, which provides HTTPS, autoscaling, health checks, and zero server management. ECS Fargate remains a supported alternative, but App Runner is the default for solo-dev simplicity.

#### Core managed services:
- **RDS PostgreSQL** (system of record, backups on)
- **S3** for object storage (uploads via presigned URLs)
- **ElastiCache Redis** (optional: caching & jobs)
- **Amazon Cognito** for Auth (JWT/OIDC)
- **AWS Secrets Manager** to inject env vars at deploy

- **Acceptance Criteria:**
  - [ ] Zero-touch deployment from main branch.
  - [ ] Stable demo > 1 week without manual intervention.
  - [ ] DB recovery drill executed.
  - [ ] Zero-touch deploy from main → ECR → App Runner start-deployment → smoke tests green → promote.

### Phase B — Production Readiness
**Goals:** Improve resilience, security, and performance.
- **Deliverables:**
  - Multi-AZ Database and replicated Cache.
  - WAF policies, Rate Limits, Secrets in Vault.
  - CDN for assets; DB Connection Pooling.
  - Blue/Green or Rolling deployments.
  - Enable Multi-AZ for RDS and add connection pooling (RDS Proxy or PgBouncer).
  - Optionally front with CloudFront and WAF; keep security headers and caching rules.
- **Acceptance Criteria:**
  - [ ] SLOs defined and met under load.
  - [ ] Successful failover drill & rollback documented.
  - [ ] Penetration test findings addressed.

### Phase C — Enterprise Features (As Needed)
**Goals:** Satisfy large client requirements.
- **Deliverables:**
  - SSO (OIDC/SAML), Audit Logs, Multi-tenant Isolation.
  - Data Residency options.
  - Cost Dashboards & Budgets.
- **Acceptance Criteria:**
  - [ ] Contractual NFRs verified.
  - [ ] DR plan validated via simulation (RPO/RTO).

---

## 17) Templates & Boilerplate
### 17.1 ADR Template
```md
# ADR-XXX: Title
## Context
## Decision
## Consequences (+/-)
## Alternatives Considered
```
### 17.2 RFC Template
```md
# RFC-XXX: Title
## Summary
## Motivation & Goals
## Non-Goals
## Design
## Security/Privacy
## Rollout/Backout
## Open Questions
```
### 17.3 PR Template (Excerpt)
- [ ] Tests added/updated  
- [ ] Docs/ADR updated  
- [ ] Feature flagged (if applicable)  
- [ ] Telemetry added  
- [ ] Security review (if applicable)

### 17.4 Docker Hardening
- Non‑root user; distroless/ubi‑minimal; `--cap-drop ALL`; read‑only FS; `/tmp` tmpfs.

#### Multi-stage Dockerfile (single image)
- **Stage 1:** Node build for Next.js → standalone output
- **Stage 2:** Python deps for FastAPI
- **Final:** copy both outputs; run as non-root, read-only filesystem, cap-drop minimal

**Sample (trimmed)**
```dockerfile
FROM node:20 AS web_build
WORKDIR /app
COPY . .
RUN corepack enable && pnpm i --frozen-lockfile
RUN pnpm -C apps/web build  # Next.js standalone

FROM python:3.12 AS api_build
WORKDIR /app
COPY . .
RUN pip install -r apps/api/requirements.txt

FROM gcr.io/distroless/base-debian12  # or debian-slim with hardening
WORKDIR /app
USER 65532:65532
COPY --from=web_build /app/apps/web/.next/standalone ./web
COPY --from=web_build /app/apps/web/public ./web/public
COPY --from=api_build /app/apps/api ./api
# If not using distroless: install python runtime minimally & pip install again
ENV PYTHONUNBUFFERED=1
EXPOSE 3000 8000
COPY docker/supervisord.conf /etc/supervisor/conf.d/app.conf
CMD ["/usr/bin/supervisord","-n"]
```

**supervisord.conf (example)**
```ini
[program:api]
command=python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
autorestart=true

[program:web]
command=node web/server.js
autorestart=true
```

#### Runtime hardening checklist
- [ ] Non-root user, read-only rootfs, minimal image, drop capabilities
- [ ] Health/ready endpoints (/healthz) for orchestration

### 17.5 Minimal CSP
```
Content-Security-Policy:
  default-src 'none';
  script-src 'self' 'sha256-...';
  style-src 'self' 'unsafe-inline';
  img-src 'self' data: https:;
  font-src 'self' https:;
  connect-src 'self' https:;
  frame-ancestors 'none';
```

---

## 18) Glossary
- **DTO:** Data Transfer Object.
- **RAG:** Retrieval‑Augmented Generation.
- **RLS:** Row Level Security.
- **SLO:** Service Level Objective.
- **TTFT:** Time to First Token.
- **NullEngine:** Deterministic, non‑LLM implementation of Intelligence.
- **DX:** Developer Experience.

---

## 19) Checklists
### 19.1 Pre‑Prod Readiness
- [ ] SLOs defined, dashboards live, alerts paging  
- [ ] RLS enabled, cross‑tenant tests passing  
- [ ] SBOM and image scan clean, secrets in KMS  
- [ ] Backups/restore tested, RPO/RTO documented  
- [ ] Feature flags in place, kill switch verified  
- [ ] OpenAPI → TS sync passing, contract tests green

### 19.2 Security Launch
- [ ] CSP/HSTS headers live  
- [ ] Admin sensitive actions require re‑auth  
- [ ] Upload AV scanning and size caps  
- [ ] Logs structured with `X-Request-Id`

---

## 20) Changelog
- **v1.0.0** — Initial consolidation of Playbook and Roadmap. Added Service Layer framework, Tooling Inventory, and detailed Operational standards.

---

## 21) Appendix: Makefile targets (local + cloud)
```makefile
APP=yourapp
GIT_SHA=$(shell git rev-parse --short HEAD)
ECR=xxxxxxxxxx.dkr.ecr.us-east-1.amazonaws.com/$(APP)
SERVICE_ARN?=arn:aws:apprunner:us-east-1:123456789012:service/yourapp/abcd1234

up:
	docker compose up -d

down:
	docker compose down -v

build:
	docker build -t $(APP):$(GIT_SHA) .

push:
	aws ecr get-login-password --region us-east-1 \
	| docker login --username AWS --password-stdin $(ECR)
	docker tag $(APP):$(GIT_SHA) $(ECR):$(GIT_SHA)
	docker push $(ECR):$(GIT_SHA)

deploy-apprunner: push
	aws apprunner start-deployment --service-arn $(SERVICE_ARN)

pause:
	aws apprunner pause-service --service-arn $(SERVICE_ARN)

resume:
	aws apprunner resume-service --service-arn $(SERVICE_ARN)
```
