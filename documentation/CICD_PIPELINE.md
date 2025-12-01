# CI/CD Pipeline Documentation

This document details the Continuous Integration and Continuous Deployment (CI/CD) pipeline for **ListingLens**, implemented using **GitHub Actions**. The pipeline ensures code quality, functionality, and deployability by automatically running tests, builds, and verifications on every code change.

## 🚀 Overview

The workflow is defined in `.github/workflows/ci.yml`. It triggers on:
*   **Push** events to `main` or `master` branches.
*   **Pull Request** events targeting `main` or `master` branches.

The pipeline consists of four main jobs that run in a specific sequence:
1.  **Backend Tests** (`backend-test`)
2.  **Frontend Build & Lint** (`frontend-build`)
3.  **End-to-End & Load Tests** (`e2e-load-test`)
4.  **Docker Build** (`docker-build`)

---

## 🛠️ Jobs Breakdown

### 1. Backend Tests (`backend-test`)
**Objective**: Verify the integrity of the Python backend API through unit and integration tests.

*   **Environment**: `ubuntu-latest`
*   **Working Directory**: `./apps/api`
*   **Key Steps**:
    1.  **Checkout Code**: Retrieves the latest code.
    2.  **Setup Python**: Installs Python 3.11 with caching for pip.
    3.  **Environment Configuration**:
        *   Installs `cryptography`.
        *   Decrypts the `.env.encrypted` file using the `ENV_PASSPHRASE` secret.
        *   Moves the decrypted `.env` file to the root for application use.
    4.  **Install Dependencies**: Installs project dependencies from `requirements.txt` and test dependencies (`pytest`, `httpx`, `pytest-asyncio`).
    5.  **Run Tests**: Executes `pytest tests/` to run the test suite.

### 2. Frontend Build (`frontend-build`)
**Objective**: Ensure the Next.js frontend compiles correctly and adheres to code standards.

*   **Environment**: `ubuntu-latest`
*   **Working Directory**: `./apps/web`
*   **Key Steps**:
    1.  **Checkout Code**: Retrieves the latest code.
    2.  **Setup Node.js**: Installs Node.js 20 with caching for npm.
    3.  **Install Dependencies**: Runs `npm ci` for a clean install of dependencies.
    4.  **Build**: Runs `npm run build` to compile the Next.js application.
    5.  **Lint**: Runs `npm run lint` to check for code style issues.
    6.  **Tests**: Currently runs linting as a placeholder (extensible for Jest/Cypress).

### 3. End-to-End & Load Tests (`e2e-load-test`)
**Objective**: Verify system stability under load and ensure all services work together.
**Dependencies**: Runs only after `backend-test` and `frontend-build` succeed.

*   **Environment**: `ubuntu-latest`
*   **Key Steps**:
    1.  **Setup Environment**: Installs Python 3.11 and dependencies (`aiohttp`, `cryptography`).
    2.  **Decrypt Secrets**: Decrypts the `.env` file required for Docker Compose configuration.
    3.  **Start Services**:
        *   Uses `docker compose -f infra/docker-compose.yml up -d` to spin up the entire stack (API, Worker, DB, Redis, Qdrant).
    4.  **Wait for Ready**: Polls the `/api/v1/health` endpoint until the API is responsive.
    5.  **Run Load Test**: Executes `apps/api/load_test.py`, which simulates traffic against the running services.
    6.  **Teardown**: Stops and removes containers using `docker compose down`.

### 4. Docker Build (`docker-build`)
**Objective**: Build production-ready Docker images for deployment.
**Dependencies**: Runs only after `e2e-load-test` succeeds.

*   **Environment**: `ubuntu-latest`
*   **Key Steps**:
    1.  **Setup**: Checkouts code and decrypts environment secrets.
    2.  **Setup Docker Buildx**: Sets up the Docker Buildx builder instance.
    3.  **Build Backend**: Builds the `listinglens-backend` image using `apps/api/Dockerfile`.
        *   Injects `GEMINI_API_KEY` as a build argument.
        *   Uses GitHub Actions cache (`type=gha`) to speed up builds.
    4.  **Build Worker**: Builds the `listinglens-worker` image (same Dockerfile as backend).
    5.  **Build Frontend**: Builds the `listinglens-frontend` image using `apps/web/Dockerfile`.

---

## 🔐 Secrets Management

The pipeline relies on encrypted environment variables for security.
*   **`ENV_PASSPHRASE`**: A repository secret used to decrypt the `infra/.env.encrypted` file. This allows sensitive configuration (like database passwords and API keys) to be stored securely in the repository in an encrypted format.

To update secrets:
1.  Modify `infra/.env` locally.
2.  Run `python3 infra/encrypt.py`.
3.  Commit the updated `infra/.env.encrypted` file.

## ✅ Quality Gates

The pipeline enforces strict quality gates:
1.  **Code Quality**: Linter checks prevent style violations.
2.  **Logic Correctness**: Unit tests ensure business logic is correct.
3.  **Integration Integrity**: E2E tests verify service communication.
4.  **Buildability**: Docker builds ensure the application can be packaged for deployment.

A failure in any step stops the pipeline, preventing broken code from reaching production artifacts.
