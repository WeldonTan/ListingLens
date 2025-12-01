# ListingLens - Property Intelligence Dashboard

**ListingLens** is an enterprise-grade property intelligence platform designed to transform unstructured real estate data into actionable insights. By leveraging advanced web scraping technologies and state-of-the-art AI, ListingLens automates the extraction, processing, and analysis of property listings, empowering users with a structured and queryable dataset.

This project follows the **Aelion Systems Engineering Playbook**, emphasizing defensible, auditable, and safe-by-default systems.

---

## 🌟 Key Features

*   **AI-Powered Extraction & Content Generation**: Utilizes **Google Gemini AI** to not only parse unstructured HTML into standardized JSON but also to generate engaging marketing copy for listings.
*   **Automated Scraping**: Employs a robust **Crawl4AI** (Playwright-based) scraping engine that navigates dynamic websites, handles interactions like clicking "Show Phone Number," and manages headless browser sessions.
*   **Real-time Processing**: Features a high-performance asynchronous task queue using **Arq** and **Redis**, allowing for efficient background processing of scraping and content generation tasks without blocking the API.
*   **Interactive Dashboard**: A modern web interface built with **Next.js 16**, **React 19**, and **Tailwind CSS v4**, providing real-time progress monitoring for both extraction and content generation.
*   **Scalable Architecture**: A microservices-based system orchestrated with Docker, ensuring separation of concerns for scalability and maintainability.
*   **Flexible Data Export**: Enables users to export processed data and generated content into both **CSV and Excel** formats for seamless integration with external tools.

---

## 🏗️ System Architecture

ListingLens is composed of several decoupled services orchestrated via Docker Compose, following the **Modular Monolith** archetype:

### 1. Frontend Service (`frontend`)
*   **Tech Stack**: Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS v4, Lucide React (Icons).
*   **Role**: The user interface layer. It is a "dumb" rendering layer that communicates with the Backend API to submit tasks and fetch data.
*   **Features**:
    *   **Dashboard**: Real-time view of current scraping sessions with status updates.
    *   **History**: Archive of all previously scraped properties with search and filtering.
    *   **Design System**: Implements Aelion Systems design guidelines with **Michroma** (headings), **Inter** (body) fonts, and a technical slate/blue aesthetic.

### 2. Backend API Service (`backend`)
*   **Tech Stack**: FastAPI, Python 3.11+, SQLAlchemy 2.0 (Async), Pydantic v2.
*   **Role**: The central orchestrator. It exposes RESTful endpoints for the frontend, manages database interactions, and enqueues jobs to the Worker.
*   **Key Components**:
    *   **Service Layer**: Business logic is encapsulated in services (e.g., `listing_service.py`), keeping routers clean.
    *   **Pydantic Models**: Ensures strict data validation and auto-generates OpenAPI documentation.

### 3. Worker Service (`worker`)
*   **Tech Stack**: Arq, Python 3.11+, Crawl4AI (Playwright), Google Gemini API.
*   **Role**: The powerhouse. It executes background tasks asynchronously to prevent blocking the API.
*   **Responsibilities**:
    *   **Task Consumption**: Dequeues scraping tasks from Redis.
    *   **Browser Automation**: Uses **Crawl4AI** (Playwright-based) to render dynamic JavaScript content and interact with page elements.
    *   **AI Extraction**: Sends sanitized HTML to **Google Gemini** to extract structured fields (price, address, agent details, etc.).
    *   **Persistence**: Saves structured results to the PostgreSQL database.

### 4. Database Service (`db`)
*   **Tech Stack**: PostgreSQL 15 (Alpine).
*   **Role**: The persistent storage layer. Stores user data, raw listing information, and processed structured data.
*   **ORM**: managed via SQLAlchemy Async Session.

### 5. Message Broker (`redis`)
*   **Tech Stack**: Redis 7 (Alpine).
*   **Role**: Acts as the high-performance message broker for Arq, managing the queue of tasks between the Backend and the Worker. Also serves as a cache for frequent data access.

### 6. Vector Database (`qdrant`)
*   **Tech Stack**: Qdrant.
*   **Role**: Prepared for future RAG (Retrieval-Augmented Generation) capabilities to allow semantic search over listing descriptions (currently provisional).

---

## 🔄 Process Flow

1.  **Task Submission**: A user pastes a list of property URLs into the Frontend dashboard.
2.  **API Request**: The Frontend sends these URLs to the Backend API (`POST /listings/scrape`).
3.  **Validation & Enqueueing**: The Backend validates the request using Pydantic, creates a task record in Postgres, and pushes a job to the Redis message queue via Arq.
4.  **Asynchronous Execution**: The Worker picks up the job from Redis.
5.  **Smart Scraping**: The Worker initializes a headless browser session (via Selenium/Playwright), navigates to the URL, and performs necessary interactions (scrolling, clicking buttons) to load full content.
6.  **AI Analysis**: The raw HTML is processed and sent to the Gemini API with a specific prompt to extract key real estate attributes.
7.  **Data Persistence**: The structured JSON response is validated and saved to the PostgreSQL database.
8.  **Real-time Update**: The Frontend polls the task status endpoint (`POST /listings/scrape/status`) to track progress and displays the newly scraped data to the user once completed.

---

## 📂 Project Structure

```
├── apps/
│   ├── api/            # FastAPI Backend & Worker
│   │   ├── app/
│   │   │   ├── api/    # Routes & Endpoints
│   │   │   ├── core/   # Config & Security
│   │   │   ├── db/     # Database Session & Base
│   │   │   ├── models/ # SQLAlchemy Models
│   │   │   ├── services/ # Business Logic (Scraper, Gemini)
│   │   │   └── worker/ # Arq Worker Settings
│   │   └── Dockerfile
│   └── web/            # Next.js Frontend
│       ├── app/        # App Router Pages
│       ├── components/ # UI Components (shadcn/ui style)
│       ├── lib/        # API Clients & Utils
│       └── Dockerfile
├── infra/              # Infrastructure Configuration
│   ├── docker-compose.yml
│   ├── Makefile
│   └── .env
├── documentation/      # Detailed Documentation
│   ├── SYSTEM_OVERVIEW.md
│   ├── UI_UX_Design_System.md
│   └── aelion_engineering_playbook.md
└── ReadMe.md           # This file
```

---

## 🚀 Getting Started

### Prerequisites

*   **Docker Desktop**: Required to run the containerized application.
    *   [Mac (Apple Silicon)](https://desktop.docker.com/mac/main/arm64/Docker.dmg)
    *   [Mac (Intel)](https://desktop.docker.com/mac/main/amd64/Docker.dmg)
    *   [Windows/Linux](https://www.docker.com/products/docker-desktop/)
*   **Google Gemini API Key**: Essential for the AI extraction feature.

### Installation & Running

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/WeldonTan/ListingLens.git
    cd ListingLens
    ```

2.  **Configure Environment**
    Create a `.env` file in the `infra/` directory for local development:
    ```env
    GEMINI_API_KEY=your_api_key_here
    ```
    Once you have created the `.env` file, run the following command to create an encrypted version of it:
    ```bash
    python3 infra/encrypt.py
    ```

3.  **Configure GitHub Secrets for CI/CD**
    For the CI/CD pipeline to work, you must add your `ENV_PASSPHRASE` as a secret in your GitHub repository:
    1.  Go to your repository on GitHub.
    2.  Navigate to **Settings** > **Secrets and variables** > **Actions**.
    3.  Click **New repository secret**.
    4.  Name the secret `ENV_PASSPHRASE`.
    5.  Paste the passphrase you used to encrypt the `.env` file into the value field.
    6.  Click **Add secret**.

4.  **Run the Start Script (Recommended)**
    This script automates the setup process, checks for Docker, and starts the services.
    ```bash
    infra/start.sh
    ```
    *Note: If you encounter permission issues, run `chmod +x infra/start.sh` first.*

5.  **Manual Start (Alternative)**
    If you prefer running Docker commands directly:
    ```bash
    cd infra
    docker compose up --build -d
    ```

### 🛠️ Development

To contribute or make changes to the codebase:

### Backend Development
The backend is located in the `apps/api/` directory.
```bash
cd apps/api
pip install -r requirements.txt
playwright install chromium  # Required for local development
uvicorn app.main:app --reload
```

To run the worker manually:
```bash
arq app.worker.WorkerSettings
```

### Running Tests
To run the backend tests:
```bash
cd apps/api
pip install pytest pytest-asyncio httpx
pytest tests/
```

### Frontend Development
The frontend is located in the `apps/web/` directory.
```bash
cd apps/web
npm install
npm run dev
```

---

## 📐 Engineering Principles

*   **Backend as Source of Truth**: All business logic resides in the Python backend. The frontend is a reflection of the backend state.
*   **Evidence over Claims**: The system logs actions and retains raw data to provide an audit trail of how decisions (extractions) were made.
*   **Configuration Management**: Secrets are managed via environment variables, never hardcoded.

---

## 📝 License

This project is licensed under the MIT License.
