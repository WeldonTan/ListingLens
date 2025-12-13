# Security Review

## Summary
- Identified high-risk configurations in the FastAPI service that expose data-modification and queue-management endpoints without authentication and with permissive CORS settings.
- Flagged supply-chain risks in the API dependencies due to unpinned or loosely pinned packages.
- Outlined remediation steps and longer-term hardening opportunities for the backend and frontend.

## Findings and Recommended Fixes

### 1) Permissive CORS configuration with credentials
**Issue:** The API enables CORS for all origins while also allowing credentials. This permits any origin to make browser-authenticated requests, risking token or session leakage to untrusted sites.

- Evidence: `allow_origins=["*"], allow_credentials=True` in the CORS middleware setup.【F:apps/api/app/main.py†L37-L44】

**Fix:**
- Replace the wildcard with an allowlist driven by `settings.BACKEND_CORS_ORIGINS` and disable credentials unless they are required.
- Example: `allow_origins=settings.BACKEND_CORS_ORIGINS`, `allow_credentials=False` (or true only for trusted origins).
- Add deployment-time validation to prevent starting when the allowlist is empty.

### 2) Unauthenticated data and queue control endpoints
**Issue:** All listing CRUD and scraping queue endpoints lack authentication/authorization dependencies. Any caller can list, delete, purge Redis, or trigger scraping tasks, enabling data destruction and denial-of-service against the worker.

- Evidence: Listing and queue routes do not enforce dependencies for authentication (e.g., `Depends(...)` for current user) and expose destructive operations like `/listings/scrape/purge` and `DELETE /listings` openly.【F:apps/api/app/api/v1/endpoints/listings.py†L16-L139】

**Fix:**
- Require authenticated users (and ideally role-based checks) on all listing CRUD and queue-management routes. Introduce a dependency that validates JWTs issued by the existing `/login/access-token` endpoint.
- Restrict purge/abort operations to admin roles and add rate limiting on job submission endpoints to prevent task flooding.
- Return 401/403 for unauthenticated/unauthorized requests.

### 3) Dependency supply-chain exposure
**Issue:** Several API dependencies are unpinned or only minimally constrained (e.g., `pydantic>=2.10.0`, `crawl4ai>=0.7.0`, `google-genai`, `python-dotenv`, `cryptography`). This allows unintended upgrades to versions with known vulnerabilities and hampers reproducible builds.

- Evidence: Unpinned or loosely pinned packages in `apps/api/requirements.txt`.【F:apps/api/requirements.txt†L16-L27】

**Fix:**
- Pin all dependencies to vetted versions and add a dependency update cadence (e.g., monthly with `pip-audit`/`safety` checks).
- Introduce a lockfile generation step (e.g., `pip-tools` or `uv lock`) and enforce it in CI.

## Future Enhancements
- **Authentication everywhere:** Extend JWT-based auth to the frontend client, store tokens securely (HTTP-only cookies or secure storage), and gate all API mutations behind role-aware permissions.
- **Observability and auditing:** Add structured audit logs for login attempts, queue mutations, and delete operations; ship them to centralized logging with alerting on anomalous patterns.
- **Abuse and DoS defenses:** Implement rate limiting (e.g., SlowAPI) for scrape and generate endpoints, and cap concurrent background jobs per user or API key.
- **Secure defaults:** Add security headers via middleware (e.g., `Strict-Transport-Security`, `Content-Security-Policy`) and disable FastAPI docs in production or protect them behind auth.
- **Secrets management:** Load secrets (DB creds, API keys) from a vault or orchestrator secret store instead of `.env`, and rotate keys regularly.
- **Automated security testing:** Incorporate SAST/DAST and dependency scanning (pip-audit, npm audit, trivy) into CI/CD with blocking severity thresholds.
