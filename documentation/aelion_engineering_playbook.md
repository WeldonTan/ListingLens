![Aelion Systems Logo](CompleteLogo_Light.png)

# Aelion Systems — Engineering Playbook & Tech Strategy
**Audience:** Engineering, Product, SRE, Security at Aelion Systems  
**Scope:** Company‑wide standards for all project types (Monolith, API, Workflow, Dashboard, Data).  

---

## Table of Contents
1. [Strategic Context & Principles](#1-strategic-context--principles)
2. [Project Archetypes & Tech Stacks](#2-project-archetypes--tech-stacks)
3. [System Architecture & Flows](#3-system-architecture--flows)
4. [Architecture & Framework](#4-architecture--framework)
5. [Configuration & Secrets](#5-configuration--secrets)
6. [API Contract & Integration Standards](#6-api-contract--integration-standards)
7. [Data Modeling & Access](#7-data-modeling--access)
8. [Frontend Standards](#8-frontend-standards)
9. [Security & Compliance](#9-security--compliance)
10. [Observability & SRE](#10-observability--sre)
11. [CI/CD & Developer Experience](#11-cicd--developer-experience-dx)
12. [Testing Strategy](#12-testing-strategy)
13. [Data Lifecycle, Backups & DR](#13-data-lifecycle-backups--dr)
14. [Intelligence & RAG (Optional)](#14-intelligence--rag-optional)
15. [Performance Engineering](#15-performance-engineering)
16. [Administrative Operations](#16-administrative-operations)
17. [Roadmap to Production](#17-roadmap-to-production-phased)
18. [Templates & Boilerplate](#18-templates--boilerplate)
19. [Glossary](#19-glossary)
20. [Checklists](#20-checklists)

---

## 1) Strategic Context & Principles
### 1.1 Purpose
Deliver enterprise‑grade systems that are **defensible**, **auditable**, and **safe by default**. Whether building a monolith, a data pipeline, or an automation workflow, our engineering choices must align with the **Aelion Systems Strategy**: to provide decisions teams can defend.

### 1.2 Core Principles
1.  **Evidence over Claims:** Every system must produce logs, citations, or audit trails. "It worked" is not enough; "Here is the proof" is the standard.
2.  **Human Authority:** High-risk actions (e.g., automated emails, payments) must have "human-in-the-loop" approval gates or robust rollback mechanisms.
3.  **Deployment Agnosticism:** Systems must run on-prem, in private VPCs, or in the cloud without code changes. Docker is our universal packaging format.
4.  **Backend as Source of Truth:** Logic lives in the backend (Python/SQL). Frontends are dumb rendering layers.
5.  **Guardrails over Guidelines:** Enforce security and quality via linters, CI checks, and framework defaults.

---

## 2) Project Archetypes & Tech Stacks
We support five primary project archetypes. Choose the one that best fits the problem space.

### 2.1 The Modular Monolith (Default)
**Use Case:** Full-stack products, SaaS applications, complex business logic with UI.  

| Category | Tool / Library | Purpose |
|---|---|---|
| **Frontend** | React 19 + Vite | SPA, Routing, UI |
| **Backend** | FastAPI (Python 3.11+) | Async API, Business Logic |
| **Database** | PostgreSQL 16 | Relational Data Store |
| **ORM** | SQLAlchemy 2.0 (Async) | Data Access |
| **Queue** | Redis 7 + Arq | Background Jobs |

**Rationale & Synergy:**
*   **React 19 + Vite & FastAPI:** Vite offers a streamlined development experience with instant server start and HMR. React 19 brings the latest UI capabilities. This decouples the frontend completely, allowing for static deployment (CDN) and simplified scaling.
*   **Type Safety:** We use Pydantic models in FastAPI to define data structures. These models automatically generate OpenAPI specifications, which are then used to generate TypeScript clients for the React frontend. This creates an end-to-end type-safe contract, reducing integration bugs.
*   **Unified Deployment:** By packaging both as a single deployable unit (or closely coupled services), we simplify operations while maintaining the flexibility to scale them independently if needed.

### 2.2 Headless API Service
**Use Case:** Backend-only services, integration layers, high-performance data gateways.  

| Category | Tool / Library | Purpose |
|---|---|---|
| **Framework** | FastAPI (Python 3.11+) | High-performance Async API |
| **Validation** | Pydantic v2 | Strict Data Validation |
| **Docs** | OpenAPI (Swagger/Redoc) | Auto-generated Contracts |
| **Auth** | OAuth2 / JWT (FastAPI Users) | Stateless Authentication |
| **Deploy** | Docker / AWS App Runner | Containerized Serverless |

**Rationale & Synergy:**
*   **Performance:** FastAPI sits on top of Starlette and Pydantic, making it one of the fastest Python frameworks available.
*   **Documentation First:** The automatic generation of interactive documentation (Swagger UI) allows frontend teams and third-party integrators to understand and test the API without reading source code.
*   **Statelessness:** Using JWTs for authentication ensures the service is stateless, allowing it to scale horizontally across any number of containers without sticky sessions.

### 2.3 Workflow Automation
**Use Case:** Complex background processes, document pipelines, multi-step approvals, ETL orchestration.  

| Category | Tool / Library | Purpose |
|---|---|---|
| **Engine** | Temporal (Mission Critical) or Arq (Simple) | Workflow Orchestration |
| **Language** | Python 3.11+ | Logic & Integrations |
| **State** | PostgreSQL | Workflow History/State |
| **Triggers** | Webhooks / Cron | Event Sources |
| **Observability**| OpenTelemetry | Trace distributed steps |

**Rationale & Synergy:**
*   **Resilience:** Temporal provides "durable execution," meaning if a process crashes or the server restarts, the workflow resumes exactly where it left off. This is critical for long-running business processes.
*   **Python Integration:** Python is the lingua franca of automation and data processing. Using Python for workflows allows us to reuse the same domain logic and models defined in our API services.

### 2.4 Dashboard & Analytics
**Use Case:** Data visualization, internal tools, reporting portals, "Conversational Analytics".  

| Category | Tool / Library | Purpose |
|---|---|---|
| **Product UI** | React 19 + Vite + Tremor / Recharts | Customer-facing Analytics |
| **Internal UI** | Streamlit / Dash | Data Science/Internal Tools |
| **Query Layer** | Cube.js / SQL (Direct) | Semantic Layer (Optional) |
| **Vis Library** | Plotly / ECharts | Complex Charts |

**Rationale & Synergy:**
*   **Speed to Value:** Streamlit allows data scientists to build interactive tools in pure Python without needing frontend skills. For customer-facing dashboards, React 19 + Vite + Tremor provides professional, responsive components out of the box.
*   **Direct Data Access:** These tools connect directly to our PostgreSQL and Analytical warehouses, reducing the need for intermediate API layers when building internal operational tools.

### 2.5 Data Pipeline & Modelling
**Use Case:** Transforming raw data (ELT), defining metrics, cleaning datasets for AI.  

| Category | Tool / Library | Purpose |
|---|---|---|
| **Transformation**| dbt (Data Build Tool) | SQL-based Transformations |
| **Orchestration** | Dagster / Airflow | Pipeline Scheduling |
| **Warehouse** | DuckDB (Local/Small) / Postgres / BigQuery | Compute Engine |
| **Quality** | Great Expectations / dbt tests | Data Validation |
| **Catalog** | DataHub / Amundsen (Optional) | Discovery & Lineage |

**Rationale & Synergy:**
*   **Software Engineering for Data:** dbt allows us to version control, test, and document our data transformations just like software code.
*   **Reproducibility:** By defining pipelines as code, we ensure that any dataset can be regenerated from source, which is a key requirement for "defensible decisions" and auditability.

---

## 3) System Architecture & Flows

The following diagram illustrates how these components interact in a typical **Modular Monolith** or **API + Workflow** setup.

```mermaid
graph TD
    User[User / Client] -->|HTTPS| CDN[CDN / Edge]
    CDN -->|React| Web[Web App (React+Vite)]
    CDN -->|API| API[API Gateway (FastAPI)]
    
    subgraph "Application Cluster"
        Web -->|gRPC/REST| API
        API -->|Read/Write| DB[(PostgreSQL)]
        API -->|Cache| Cache[(Redis)]
        API -->|Enqueue| Queue[(Redis Queue)]
        
        Worker[Worker (Arq/Temporal)] -->|Dequeue| Queue
        Worker -->|Read/Write| DB
        Worker -->|Vector Search| VectorDB[(Qdrant)]
    end
    
    subgraph "External / AI"
        Worker -->|Inference| LLM[LLM Provider]
        Worker -->|Storage| S3[Object Storage]
    end
    
    classDef storage fill:#f9f,stroke:#333,stroke-width:2px;
    class DB,Cache,Queue,VectorDB,S3 storage;
```

**Flow Description:**
1.  **User Interaction:** Users interact with the **React 19 + Vite** frontend. Static assets are served via CDN.
2.  **API Requests:** Dynamic data fetches are sent to the **FastAPI** Gateway.
3.  **Synchronous Logic:** The API handles immediate logic (validation, simple reads/writes) using **PostgreSQL** and **Redis** (for caching).
4.  **Asynchronous Tasks:** Heavy tasks (generating reports, AI inference) are offloaded to the **Redis Queue**.
5.  **Worker Execution:** **Workers** pick up tasks, perform computations (potentially calling external **LLMs** or **Vector DBs**), and update the **PostgreSQL** database with results.
6.  **Data Persistence:** Files are stored in **S3**, while structured data remains in **PostgreSQL**.

---

## 4) Architecture & Framework
*(Applies to all archetypes, with Monolith as the reference implementation)*

### 4.1 Service Layer Pattern
Regardless of the archetype, business logic belongs in a **Service Layer**, not in controllers (API routes) or UI components.
- **Routes:** Parse input, call service, return response.
- **Services:** Execute logic, talk to DB/External APIs.
- **Models:** Define data structure.

### 4.2 Logical Modules
Group code by **Feature** (e.g., `auth`, `billing`, `reporting`), not by technical layer (e.g., `controllers`, `models`).
```
apps/api/app/
  services/
    auth/
    billing/
    reporting/
```

---

## 5) Configuration & Secrets
- **Strict Separation:** Code in Git; Config in Environment Variables.
- **Secret Management:** AWS Secrets Manager (Prod), `.env` (Local).
- **Validation:** Use `pydantic-settings` to validate env vars at startup. Fail fast if missing.

---

## 6) API Contract & Integration Standards
- **Format:** JSON, snake_case keys.
- **Schema:** OpenAPI 3.1 (generated from Pydantic).
- **Versioning:** URI Versioning (`/api/v1/...`).
- **Error Handling:** Standardized error envelope with `code`, `message`, `request_id`.

---

## 7) Data Modeling & Access
- **PostgreSQL** is the default for transactional data.
- **SQLAlchemy 2.0** (Async) for Python services.
- **dbt** for analytical transformations and complex reporting views.
- **Migrations:** Alembic is mandatory for schema changes. No manual DDL.

---

## 8) Frontend Standards
*(For Monolith and Dashboard archetypes)*
- **Modern Tech Stack**: Built with React 19 + Vite for blazing fast performance and minimal setup
- **Sophisticated Design**: Tailwind CSS v4 styling with Michroma (headings) and Inter (body) fonts
- **Visuals**: "Google-like" clean aesthetic. Blue/Black/White palette.
- **Smooth Animations**: Framer Motion transitions for pages and interactive elements

---

## 9) Security & Compliance
- **Auth:** OAuth2 + JWT. Short-lived access tokens (15m), rotating refresh tokens.
- **RBAC:** Enforced at the Service Layer.
- **Audit Logs:** **CRITICAL**. Every write action must be logged to an immutable audit table (`actor_id`, `action`, `resource`, `timestamp`).
- **Supply Chain:** Scanned Docker images, pinned dependencies.

---

## 10) Observability & SRE
- **Standard:** OpenTelemetry (OTel).
- **Signals:** Traces (Latency), Metrics (Traffic, Errors, Saturation), Logs (Structured JSON).
- **Correlation:** `X-Request-Id` propagated across all services (API -> Worker -> DB).

---

## 11) CI/CD & Developer Experience (DX)
- **Repo:** Monorepo (Turborepo or simple folder structure) preferred.
- **Local:** `docker compose up` should start the entire stack.
- **Pipeline:**
    1. Lint/Format (Ruff/Biome).
    2. Test (Pytest/Vitest).
    3. Build Container.
    4. Scan (Trivy).
    5. Deploy (App Runner / ECS).

---

## 12) Testing Strategy
- **Unit:** Logic in Services.
- **Integration:** API endpoints with DB fixtures.
- **E2E:** Critical user flows (Playwright).
- **Data:** `dbt test` for data pipelines.

---

## 13) Data Lifecycle, Backups & DR
- **RPO/RTO:** 5m / 30m.
- **Backups:** PITR for Postgres. S3 Versioning for artifacts.
- **Retention:** Enforce TTLs on sensitive data.

---

## 14) Intelligence & RAG (Optional)
- **Engine:** `IntelligenceEngine` protocol (swap providers easily).
- **Vector DB:** Qdrant.
- **Safety:** Guardrails on inputs (Prompt Injection) and outputs (Hallucination check).
- **Evidence:** RAG answers must cite source documents.

---

## 15) Performance Engineering
- **Async First:** Python `asyncio` for I/O bound tasks.
- **Caching:** Redis for hot data.
- **Optimization:** Database indexing, query analysis.

---

## 16) Administrative Operations
- **Back-office:** Admin panels for tenant management.
- **Feature Flags:** Decouple deploy from release.

---

## 17) Roadmap to Production (Phased)
- **Phase A:** Local Hardening & Staging (Docker, CI/CD).
- **Phase B:** Production Readiness (HA, Security, WAF).
- **Phase C:** Enterprise Features (SSO, Audit, Compliance).

---

## 18) Templates & Boilerplate
*(Refer to previous documentation for specific Dockerfiles and Configs)*

---

## 19) Glossary
- **DTO:** Data Transfer Object.
- **ELT:** Extract, Load, Transform.
- **RAG:** Retrieval-Augmented Generation.
- **SLO:** Service Level Objective.

---

## 20) Checklists
- [ ] **Audit Logging:** Is every write action logged?
- [ ] **Security:** Are secrets managed properly?
- [ ] **Observability:** Are traces propagating?
- [ ] **Backups:** Is PITR enabled?
